#!/usr/bin/env python3
"""qdpx_merge.py - Merge coding work from one QDPX into another.

Usage:
    python .cursor/skills/qdpx/qdpx_merge.py --base "Thesis-manual.qdpx" --incoming "Thesis-erik.qdpx" --out "Thesis-merged.qdpx"

Behavior:
    - Keeps all data in --base.
    - Adds missing codes, quotations (PlainTextSelection codings), notes, and sources
      from --incoming.
    - For overlapping quotations, unions code assignments by code path.
"""

from __future__ import annotations

import argparse
import copy
import sys
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

QDA_NS = "urn:QDA-XML:project:1.0"
NS = {"q": QDA_NS}
ET.register_namespace("", QDA_NS)


class CliError(Exception):
    """Raised for user-facing CLI input errors."""


@dataclass
class MergeStats:
    added_codes: int = 0
    added_sources: int = 0
    added_selections: int = 0
    added_codings: int = 0
    added_notes: int = 0
    skipped_notes_as_duplicate: int = 0


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load_qde(path: Path) -> tuple[ET.Element, zipfile.ZipFile]:
    try:
        zf = zipfile.ZipFile(path, "r")
    except FileNotFoundError as exc:
        raise CliError(f"QDPX not found: {path}") from exc
    except zipfile.BadZipFile as exc:
        raise CliError(f"Invalid zip/QDPX file: {path}") from exc

    try:
        root = ET.fromstring(zf.read("project.qde"))
    except KeyError as exc:
        zf.close()
        raise CliError(f"QDPX missing project.qde: {path}") from exc

    return root, zf


def _sources_parent(root: ET.Element) -> ET.Element:
    parent = root.find("q:Sources", NS)
    if parent is None:
        parent = ET.SubElement(root, f"{{{QDA_NS}}}Sources")
    return parent


def _notes_parent(root: ET.Element) -> ET.Element:
    parent = root.find("q:Notes", NS)
    if parent is None:
        parent = ET.SubElement(root, f"{{{QDA_NS}}}Notes")
    return parent


def _codebook_root(root: ET.Element) -> ET.Element:
    cb = root.find("q:CodeBook", NS)
    if cb is None:
        cb = ET.SubElement(root, f"{{{QDA_NS}}}CodeBook")
    codes = cb.find("q:Codes", NS)
    if codes is None:
        codes = ET.SubElement(cb, f"{{{QDA_NS}}}Codes")
    return codes


def _iter_codes_with_path(parent: ET.Element, prefix: list[str]) -> list[tuple[ET.Element, list[str]]]:
    out: list[tuple[ET.Element, list[str]]] = []
    for c in parent.findall("q:Code", NS):
        name = c.attrib.get("name", "")
        path = [*prefix, name]
        out.append((c, path))
        out.extend(_iter_codes_with_path(c, path))
    return out


def _full_path(parts: list[str]) -> str:
    return ": ".join(parts)


def _guid_upper(guid: str) -> str:
    return guid.upper()


def _read_internal_text(zf: zipfile.ZipFile, internal_path: str) -> str:
    rel = internal_path.replace("internal://", "").lstrip("/")
    if not rel:
        return ""
    archive_path = f"sources/{rel}"
    try:
        data = zf.read(archive_path)
    except KeyError:
        return ""
    return data.decode("utf-8", errors="replace")


def _ensure_code_path(
    base_codes_root: ET.Element,
    parts: list[str],
    incoming_code_elem: ET.Element,
    base_guid_to_full: dict[str, str],
    base_full_to_guid: dict[str, str],
    stats: MergeStats,
) -> str:
    if not parts:
        raise CliError("Encountered invalid empty code path while merging.")

    full = _full_path(parts)
    existing = base_full_to_guid.get(full)
    if existing:
        return existing

    parent = base_codes_root
    built: list[str] = []

    for idx, part in enumerate(parts):
        built.append(part)
        current_full = _full_path(built)
        guid = base_full_to_guid.get(current_full)
        if guid:
            for child in parent.findall("q:Code", NS):
                if _guid_upper(child.attrib.get("guid", "")) == guid:
                    parent = child
                    break
            continue

        attrs = {
            "guid": str(uuid.uuid4()).upper(),
            "name": part,
            "isCodable": incoming_code_elem.attrib.get("isCodable", "true"),
        }
        new_code = ET.SubElement(parent, f"{{{QDA_NS}}}Code", attrs)

        if idx == len(parts) - 1:
            incoming_desc = incoming_code_elem.find("q:Description", NS)
            if incoming_desc is not None and (incoming_desc.text or "").strip():
                desc = ET.SubElement(new_code, f"{{{QDA_NS}}}Description")
                desc.text = (incoming_desc.text or "").strip()

        base_full_to_guid[current_full] = attrs["guid"]
        base_guid_to_full[attrs["guid"]] = current_full
        parent = new_code
        stats.added_codes += 1

    return base_full_to_guid[full]


def _selection_span_key(sel: ET.Element) -> tuple[str, str]:
    return sel.attrib.get("startPosition", ""), sel.attrib.get("endPosition", "")


def _source_text_from_attr(src: ET.Element, zf: zipfile.ZipFile) -> str:
    p = src.attrib.get("plainTextPath", "")
    if not p:
        return ""
    return _read_internal_text(zf, p)


def _copy_referenced_source_file(
    zf: zipfile.ZipFile,
    internal_path: str,
    extra_files: dict[str, bytes],
    existing_names: set[str],
) -> None:
    rel = internal_path.replace("internal://", "").lstrip("/")
    if not rel:
        return
    archive_path = f"sources/{rel}"
    if archive_path in existing_names or archive_path in extra_files:
        return
    try:
        extra_files[archive_path] = zf.read(archive_path)
    except KeyError:
        return


def _map_code_guids(base_root: ET.Element, incoming_root: ET.Element, stats: MergeStats) -> dict[str, str]:
    base_codes_root = _codebook_root(base_root)
    incoming_codes_root = _codebook_root(incoming_root)

    base_guid_to_full: dict[str, str] = {}
    base_full_to_guid: dict[str, str] = {}
    for code, parts in _iter_codes_with_path(base_codes_root, []):
        g = _guid_upper(code.attrib.get("guid", ""))
        if not g:
            continue
        full = _full_path(parts)
        base_guid_to_full[g] = full
        base_full_to_guid[full] = g

    incoming_guid_to_path: dict[str, list[str]] = {}
    incoming_guid_to_elem: dict[str, ET.Element] = {}
    for code, parts in _iter_codes_with_path(incoming_codes_root, []):
        g = _guid_upper(code.attrib.get("guid", ""))
        if not g:
            continue
        incoming_guid_to_path[g] = parts
        incoming_guid_to_elem[g] = code

    code_map: dict[str, str] = {}
    for inc_guid, parts in incoming_guid_to_path.items():
        full = _full_path(parts)
        if inc_guid in base_guid_to_full:
            code_map[inc_guid] = inc_guid
            continue

        existing_by_path = base_full_to_guid.get(full)
        if existing_by_path:
            code_map[inc_guid] = existing_by_path
            continue

        mapped = _ensure_code_path(
            base_codes_root=base_codes_root,
            parts=parts,
            incoming_code_elem=incoming_guid_to_elem[inc_guid],
            base_guid_to_full=base_guid_to_full,
            base_full_to_guid=base_full_to_guid,
            stats=stats,
        )
        code_map[inc_guid] = mapped

    return code_map


def _collect_existing_refs(sel: ET.Element) -> set[str]:
    out: set[str] = set()
    for coding in sel.findall("q:Coding", NS):
        for ref in coding.findall("q:CodeRef", NS):
            tgt = _guid_upper(ref.attrib.get("targetGUID", ""))
            if tgt:
                out.add(tgt)
    return out


def _merge_selection_codings(target_sel: ET.Element, incoming_sel: ET.Element, code_map: dict[str, str], stats: MergeStats) -> None:
    existing_refs = _collect_existing_refs(target_sel)
    now = _now_utc()
    creating_user = target_sel.attrib.get("creatingUser", incoming_sel.attrib.get("creatingUser", ""))

    for coding in incoming_sel.findall("q:Coding", NS):
        for ref in coding.findall("q:CodeRef", NS):
            incoming_tgt = _guid_upper(ref.attrib.get("targetGUID", ""))
            if not incoming_tgt:
                continue
            mapped_tgt = code_map.get(incoming_tgt)
            if not mapped_tgt or mapped_tgt in existing_refs:
                continue

            new_coding = ET.SubElement(
                target_sel,
                f"{{{QDA_NS}}}Coding",
                {
                    "guid": str(uuid.uuid4()).upper(),
                    "creatingUser": creating_user,
                    "creationDateTime": now,
                },
            )
            ET.SubElement(new_coding, f"{{{QDA_NS}}}CodeRef", {"targetGUID": mapped_tgt})
            existing_refs.add(mapped_tgt)
            stats.added_codings += 1


def _remap_selection_codes_inplace(sel: ET.Element, code_map: dict[str, str]) -> None:
    for coding in list(sel.findall("q:Coding", NS)):
        kept = 0
        for ref in list(coding.findall("q:CodeRef", NS)):
            tgt = _guid_upper(ref.attrib.get("targetGUID", ""))
            mapped = code_map.get(tgt)
            if not mapped:
                coding.remove(ref)
                continue
            ref.attrib["targetGUID"] = mapped
            kept += 1
        if kept == 0:
            sel.remove(coding)


def _merge_sources(
    base_root: ET.Element,
    incoming_root: ET.Element,
    base_zip: zipfile.ZipFile,
    incoming_zip: zipfile.ZipFile,
    code_map: dict[str, str],
    extra_files: dict[str, bytes],
    existing_names: set[str],
    stats: MergeStats,
) -> None:
    base_sources_parent = _sources_parent(base_root)
    incoming_sources_parent = _sources_parent(incoming_root)

    base_by_guid: dict[str, ET.Element] = {}
    base_by_name: dict[str, list[ET.Element]] = {}

    for s in base_sources_parent.findall("q:TextSource", NS):
        g = _guid_upper(s.attrib.get("guid", ""))
        if g:
            base_by_guid[g] = s
        n = s.attrib.get("name", "")
        base_by_name.setdefault(n, []).append(s)

    for inc_src in incoming_sources_parent.findall("q:TextSource", NS):
        inc_guid = _guid_upper(inc_src.attrib.get("guid", ""))
        inc_name = inc_src.attrib.get("name", "")

        target_src = base_by_guid.get(inc_guid)

        if target_src is None and inc_name in base_by_name and len(base_by_name[inc_name]) == 1:
            candidate = base_by_name[inc_name][0]
            base_text = _source_text_from_attr(candidate, base_zip)
            inc_text = _source_text_from_attr(inc_src, incoming_zip)
            if base_text and inc_text and base_text == inc_text:
                target_src = candidate

        if target_src is None:
            cloned = copy.deepcopy(inc_src)
            _remap_selection_codes_inplace(cloned, code_map)
            base_sources_parent.append(cloned)
            stats.added_sources += 1

            new_guid = _guid_upper(cloned.attrib.get("guid", ""))
            if new_guid:
                base_by_guid[new_guid] = cloned
            base_by_name.setdefault(inc_name, []).append(cloned)

            plain_path = cloned.attrib.get("plainTextPath", "")
            rich_path = cloned.attrib.get("richTextPath", "")
            _copy_referenced_source_file(incoming_zip, plain_path, extra_files, existing_names)
            _copy_referenced_source_file(incoming_zip, rich_path, extra_files, existing_names)
            continue

        existing_sel_by_guid: dict[str, ET.Element] = {}
        existing_sel_by_span: dict[tuple[str, str], ET.Element] = {}
        for sel in target_src.findall("q:PlainTextSelection", NS):
            sg = _guid_upper(sel.attrib.get("guid", ""))
            if sg:
                existing_sel_by_guid[sg] = sel
            existing_sel_by_span[_selection_span_key(sel)] = sel

        for inc_sel in inc_src.findall("q:PlainTextSelection", NS):
            inc_sel_guid = _guid_upper(inc_sel.attrib.get("guid", ""))
            target_sel = existing_sel_by_guid.get(inc_sel_guid)
            if target_sel is None:
                target_sel = existing_sel_by_span.get(_selection_span_key(inc_sel))

            if target_sel is not None:
                _merge_selection_codings(target_sel, inc_sel, code_map, stats)
                continue

            cloned_sel = copy.deepcopy(inc_sel)
            _remap_selection_codes_inplace(cloned_sel, code_map)
            target_src.append(cloned_sel)
            stats.added_selections += 1
            stats.added_codings += len(cloned_sel.findall("q:Coding", NS))


def _merge_notes(
    base_root: ET.Element,
    incoming_root: ET.Element,
    base_zip: zipfile.ZipFile,
    incoming_zip: zipfile.ZipFile,
    extra_files: dict[str, bytes],
    existing_names: set[str],
    stats: MergeStats,
) -> None:
    base_notes_parent = _notes_parent(base_root)
    incoming_notes_parent = _notes_parent(incoming_root)

    base_by_guid: dict[str, ET.Element] = {}
    base_by_title_body: set[tuple[str, str]] = set()

    for note in base_notes_parent.findall("q:Note", NS):
        g = _guid_upper(note.attrib.get("guid", ""))
        if g:
            base_by_guid[g] = note
        title = note.attrib.get("name", "")
        body = _read_internal_text(base_zip, note.attrib.get("plainTextPath", ""))
        base_by_title_body.add((title, body))

    for inc_note in incoming_notes_parent.findall("q:Note", NS):
        g = _guid_upper(inc_note.attrib.get("guid", ""))
        if g and g in base_by_guid:
            continue

        title = inc_note.attrib.get("name", "")
        body = _read_internal_text(incoming_zip, inc_note.attrib.get("plainTextPath", ""))
        if (title, body) in base_by_title_body:
            stats.skipped_notes_as_duplicate += 1
            continue

        cloned = copy.deepcopy(inc_note)
        base_notes_parent.append(cloned)
        stats.added_notes += 1
        base_by_title_body.add((title, body))

        plain_path = cloned.attrib.get("plainTextPath", "")
        rich_path = cloned.attrib.get("richTextPath", "")
        _copy_referenced_source_file(incoming_zip, plain_path, extra_files, existing_names)
        _copy_referenced_source_file(incoming_zip, rich_path, extra_files, existing_names)


def run_merge(base_qdpx: Path, incoming_qdpx: Path, out_qdpx: Path) -> MergeStats:
    if not base_qdpx.exists():
        raise CliError(f"Base QDPX not found: {base_qdpx}")
    if not incoming_qdpx.exists():
        raise CliError(f"Incoming QDPX not found: {incoming_qdpx}")
    if base_qdpx.resolve() == incoming_qdpx.resolve():
        raise CliError("--base and --incoming must be different files.")

    stats = MergeStats()
    extra_files: dict[str, bytes] = {}

    base_root, base_zip = _load_qde(base_qdpx)
    incoming_root, incoming_zip = _load_qde(incoming_qdpx)

    try:
        existing_names = set(base_zip.namelist())

        code_map = _map_code_guids(base_root, incoming_root, stats)
        _merge_sources(
            base_root=base_root,
            incoming_root=incoming_root,
            base_zip=base_zip,
            incoming_zip=incoming_zip,
            code_map=code_map,
            extra_files=extra_files,
            existing_names=existing_names,
            stats=stats,
        )
        _merge_notes(
            base_root=base_root,
            incoming_root=incoming_root,
            base_zip=base_zip,
            incoming_zip=incoming_zip,
            extra_files=extra_files,
            existing_names=existing_names,
            stats=stats,
        )

        xml_data = ET.tostring(base_root, encoding="utf-8", xml_declaration=True)

        with zipfile.ZipFile(out_qdpx, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            written: set[str] = set()
            for info in base_zip.infolist():
                data = base_zip.read(info.filename)
                if info.filename == "project.qde":
                    data = xml_data
                zout.writestr(info, data)
                written.add(info.filename)

            for name, data in extra_files.items():
                if name in written:
                    continue
                zout.writestr(name, data)
                written.add(name)

    finally:
        base_zip.close()
        incoming_zip.close()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge coding from one QDPX into another.")
    parser.add_argument("--base", type=Path, required=True, help="Base/main QDPX to keep as starting point.")
    parser.add_argument("--incoming", type=Path, required=True, help="Incoming QDPX to merge into base.")
    parser.add_argument("--out", type=Path, required=True, help="Merged output QDPX path.")
    args = parser.parse_args()

    base = args.base.resolve()
    incoming = args.incoming.resolve()
    out = args.out.resolve()

    try:
        stats = run_merge(base_qdpx=base, incoming_qdpx=incoming, out_qdpx=out)
        print(f"Base QDPX: {base}")
        print(f"Incoming QDPX: {incoming}")
        print(f"Output QDPX: {out}")
        print(
            "Merged: "
            f"{stats.added_codes} code(s), "
            f"{stats.added_sources} source(s), "
            f"{stats.added_selections} selection(s), "
            f"{stats.added_codings} coding(s), "
            f"{stats.added_notes} note(s)"
        )
        if stats.skipped_notes_as_duplicate:
            print(f"Skipped duplicate notes: {stats.skipped_notes_as_duplicate}")
    except CliError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
