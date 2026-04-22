#!/usr/bin/env python3
"""qdpx_export.py - Apply Markdown workspace edits back into a QDPX archive.

This exporter is full-project only: it applies all editable changes found in
the workspace (`codebook.md`, `memos.md`, `quotations/*.md`) to a base QDPX
and writes a new QDPX output file.

Usage:
    python .cursor/skills/qdpx/qdpx_export.py --base "Thesis.qdpx" --in qdpx-coding --out "Thesis-updated.qdpx"
"""

from __future__ import annotations

import argparse
import re
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

SKILL_DIR = Path(__file__).parent
WORKSPACE_ROOT = SKILL_DIR.parent.parent.parent
DEFAULT_WORKSPACE = WORKSPACE_ROOT / "qdpx-coding"

CODE_ID_RE = re.compile(r"<!--\s*id:\s*([A-Fa-f0-9\-]{32,36})\s*-->")
DESC_RE = re.compile(r"\*\*Description\*\*:\s*(.*)")
MEMO_BLOCK_RE = re.compile(
    r"^##\s+(?P<title>.+?)\n<!--\s*id:\s*(?P<id>[A-Fa-f0-9\-]{32,36})\s*-->\n\n?(?P<body>.*?)(?:\n---\n|\Z)",
    re.MULTILINE | re.DOTALL,
)
QUOTE_BLOCK_RE = re.compile(
    r"^##\s+Quotation\s+\d+\n<!--\s*id:\s*(?P<id>[A-Fa-f0-9\-]{32,36})\s*-->\n(?:<!--\s*span:[^\n]*\n)?\*\*Codes\*\*:\s*(?P<codes>.*)$",
    re.MULTILINE,
)


class CliError(Exception):
    """Raised for user-facing CLI input errors."""


@dataclass
class CodebookEdit:
    guid: str
    heading: str
    description: str


@dataclass
class MemoEdit:
    guid: str
    title: str
    body: str


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _find_default_qdpx() -> Path:
    files = sorted(WORKSPACE_ROOT.glob("*.qdpx"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise CliError("No .qdpx files found in workspace root.")
    return files[0]


def _parse_codebook(path: Path) -> list[CodebookEdit]:
    if not path.exists():
        raise CliError(f"Missing codebook file: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    edits: list[CodebookEdit] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.startswith("## "):
            i += 1
            continue

        heading = line[3:].strip()
        j = i + 1
        block_end = len(lines)
        while j < len(lines):
            if lines[j].startswith("## "):
                block_end = j
                break
            j += 1

        block = "\n".join(lines[i:block_end])
        id_match = CODE_ID_RE.search(block)
        if not id_match:
            i = block_end
            continue
        guid = id_match.group(1).upper()

        desc_match = DESC_RE.search(block)
        description = ""
        if desc_match:
            raw = desc_match.group(1).strip()
            if raw != "*(not set)*":
                description = raw

        edits.append(CodebookEdit(guid=guid, heading=heading, description=description))
        i = block_end

    return edits


def _parse_memos(path: Path) -> list[MemoEdit]:
    if not path.exists():
        raise CliError(f"Missing memos file: {path}")
    text = path.read_text(encoding="utf-8")
    edits: list[MemoEdit] = []
    for m in MEMO_BLOCK_RE.finditer(text):
        guid = m.group("id").upper()
        title = m.group("title").strip()
        body = m.group("body").rstrip("\n")
        if body.strip() == "*(empty)*":
            body = ""
        edits.append(MemoEdit(guid=guid, title=title, body=body))
    return edits


def _parse_quote_codes(workspace_dir: Path) -> dict[str, list[str]]:
    quotes_dir = workspace_dir / "quotations"
    if not quotes_dir.exists():
        raise CliError(f"Missing quotations directory: {quotes_dir}")

    quote_codes: dict[str, list[str]] = {}
    for md in sorted(quotes_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        for m in QUOTE_BLOCK_RE.finditer(text):
            guid = m.group("id").upper()
            raw_codes = m.group("codes").strip()
            if raw_codes == "*(none)*":
                quote_codes[guid] = []
                continue
            names = [c.strip() for c in re.findall(r"`([^`]+)`", raw_codes)]
            deduped: list[str] = []
            seen: set[str] = set()
            for n in names:
                if n not in seen:
                    deduped.append(n)
                    seen.add(n)
            quote_codes[guid] = deduped
    return quote_codes


def _code_tree_maps(
    codes_root: ET.Element,
) -> tuple[dict[str, ET.Element], dict[str, str], dict[str, str], dict[str, list[str]], dict[str, str]]:
    guid_to_elem: dict[str, ET.Element] = {}
    full_to_guid: dict[str, str] = {}
    guid_to_full: dict[str, str] = {}
    leaf_to_guids: dict[str, list[str]] = {}
    guid_to_parent_full: dict[str, str] = {}

    def walk(parent: ET.Element, prefix: list[str]) -> None:
        for code in parent.findall("q:Code", NS):
            guid = code.attrib.get("guid", "").upper()
            name = code.attrib.get("name", "")
            full = ": ".join(prefix + [name]) if prefix else name
            if guid:
                guid_to_elem[guid] = code
                full_to_guid[full] = guid
                guid_to_full[guid] = full
                leaf_to_guids.setdefault(name, []).append(guid)
                guid_to_parent_full[guid] = ": ".join(prefix)
            walk(code, prefix + [name])

    walk(codes_root, [])
    return guid_to_elem, full_to_guid, guid_to_full, leaf_to_guids, guid_to_parent_full


def _ensure_code_by_path(
    code_name: str,
    codes_root: ET.Element,
    guid_to_elem: dict[str, ET.Element],
    full_to_guid: dict[str, str],
    guid_to_full: dict[str, str],
    leaf_to_guids: dict[str, list[str]],
) -> str:
    if code_name in full_to_guid:
        return full_to_guid[code_name]
    leaf_hits = leaf_to_guids.get(code_name, [])
    if len(leaf_hits) == 1:
        return leaf_hits[0]

    parts = [p.strip() for p in code_name.split(":") if p.strip()]
    if not parts:
        raise CliError(f"Invalid code name in quotations markdown: {code_name!r}")

    parent = codes_root
    prefix: list[str] = []
    for idx, part in enumerate(parts):
        found = None
        for child in parent.findall("q:Code", NS):
            if child.attrib.get("name", "") == part:
                found = child
                break

        if found is None:
            new_guid = str(uuid.uuid4()).upper()
            found = ET.SubElement(
                parent,
                f"{{{QDA_NS}}}Code",
                {
                    "guid": new_guid,
                    "name": part,
                    "isCodable": "true",
                },
            )

            full = ": ".join(prefix + [part]) if prefix else part
            guid_to_elem[new_guid] = found
            full_to_guid[full] = new_guid
            guid_to_full[new_guid] = full
            leaf_to_guids.setdefault(part, []).append(new_guid)

        parent = found
        prefix.append(part)

    created_full = ": ".join(parts)
    return full_to_guid[created_full]


def run_export(base_qdpx: Path, workspace_dir: Path, out_qdpx: Path) -> None:
    if not base_qdpx.exists():
        raise CliError(f"Base QDPX not found: {base_qdpx}")
    if not workspace_dir.exists():
        raise CliError(f"Workspace directory not found: {workspace_dir}")

    codebook_edits = _parse_codebook(workspace_dir / "codebook.md")
    memo_edits = _parse_memos(workspace_dir / "memos.md")
    quote_codes = _parse_quote_codes(workspace_dir)

    with zipfile.ZipFile(base_qdpx, "r") as zin:
        try:
            root = ET.fromstring(zin.read("project.qde"))
        except KeyError as exc:
            raise CliError("Base QDPX missing project.qde") from exc

        codes_root = root.find("q:CodeBook/q:Codes", NS)
        if codes_root is None:
            raise CliError("project.qde missing CodeBook/Codes")

        notes_by_guid: dict[str, ET.Element] = {}
        for note in root.findall("q:Notes/q:Note", NS):
            guid = note.attrib.get("guid", "").upper()
            if guid:
                notes_by_guid[guid] = note

        selections_by_guid: dict[str, ET.Element] = {}
        for sel in root.findall(".//q:PlainTextSelection", NS):
            guid = sel.attrib.get("guid", "").upper()
            if guid:
                selections_by_guid[guid] = sel

        guid_to_elem, full_to_guid, guid_to_full, leaf_to_guids, guid_to_parent_full = _code_tree_maps(codes_root)

        warnings: list[str] = []

        # Apply codebook edits: rename leaf and description by id.
        renamed = 0
        desc_updated = 0
        for edit in codebook_edits:
            elem = guid_to_elem.get(edit.guid)
            if elem is None:
                warnings.append(f"Code id not found in base QDPX: {edit.guid}")
                continue

            old_full = guid_to_full.get(edit.guid, elem.attrib.get("name", ""))
            old_leaf = elem.attrib.get("name", "")
            parent_prefix = guid_to_parent_full.get(edit.guid, "")

            if not edit.heading.strip():
                continue

            # IMPORTANT: many top-level codes intentionally contain ":" in the name.
            # Only strip a parent prefix when it exactly matches the current tree path.
            if parent_prefix:
                prefix = parent_prefix + ": "
                if edit.heading.startswith(prefix):
                    new_leaf = edit.heading[len(prefix) :]
                else:
                    new_leaf = edit.heading
                    if ": " in edit.heading:
                        warnings.append(
                            f"Code re-parenting is not supported in export; keeping existing parent for {edit.guid}."
                        )
            else:
                new_leaf = edit.heading

            if not new_leaf.strip():
                warnings.append(f"Skipping empty code name after parse for {edit.guid}")
                continue

            if parent_prefix and ": " in edit.heading and not edit.heading.startswith(parent_prefix + ": "):
                warnings.append(
                    f"Code heading appears to move parent path; re-parenting skipped for {edit.guid}."
                )

            if new_leaf != old_leaf:
                elem.attrib["name"] = new_leaf
                renamed += 1

            desc_elem = elem.find("q:Description", NS)
            if desc_elem is None:
                desc_elem = ET.SubElement(elem, f"{{{QDA_NS}}}Description")
            current_desc = (desc_elem.text or "").strip()
            new_desc = edit.description.strip()
            if current_desc != new_desc:
                desc_elem.text = new_desc
                desc_updated += 1

        # Rebuild code maps after any rename.
        guid_to_elem, full_to_guid, guid_to_full, leaf_to_guids, guid_to_parent_full = _code_tree_maps(codes_root)

        # Apply memo edits and collect updated source text blobs.
        updated_source_files: dict[str, bytes] = {}
        memos_updated = 0
        for memo in memo_edits:
            note = notes_by_guid.get(memo.guid)
            if note is None:
                warnings.append(f"Memo id not found in base QDPX: {memo.guid}")
                continue
            note.attrib["name"] = memo.title
            path_attr = note.attrib.get("plainTextPath", "")
            if not path_attr:
                warnings.append(f"Memo {memo.guid} has no plainTextPath; title updated only.")
                continue
            rel = path_attr.replace("internal://", "").lstrip("/")
            archive_path = f"sources/{rel}"
            updated_source_files[archive_path] = memo.body.encode("utf-8")
            memos_updated += 1

        # Apply quotation code-line edits by selection id.
        now = _now_utc()
        quote_updates = 0
        for sel_guid, code_names in quote_codes.items():
            sel = selections_by_guid.get(sel_guid)
            if sel is None:
                warnings.append(f"Quotation id not found in base QDPX: {sel_guid}")
                continue

            resolved_code_guids: list[str] = []
            for code_name in code_names:
                code_guid = _ensure_code_by_path(
                    code_name,
                    codes_root,
                    guid_to_elem,
                    full_to_guid,
                    guid_to_full,
                    leaf_to_guids,
                )
                if code_guid not in resolved_code_guids:
                    resolved_code_guids.append(code_guid)

            for child in list(sel):
                if child.tag == f"{{{QDA_NS}}}Coding":
                    sel.remove(child)

            creating_user = sel.attrib.get("creatingUser", "")
            for code_guid in resolved_code_guids:
                coding = ET.SubElement(
                    sel,
                    f"{{{QDA_NS}}}Coding",
                    {
                        "guid": str(uuid.uuid4()).upper(),
                        "creatingUser": creating_user,
                        "creationDateTime": now,
                    },
                )
                ET.SubElement(coding, f"{{{QDA_NS}}}CodeRef", {"targetGUID": code_guid})

            quote_updates += 1

        xml_data = ET.tostring(root, encoding="utf-8", xml_declaration=True)

        with zipfile.ZipFile(out_qdpx, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename == "project.qde":
                    data = xml_data
                elif info.filename in updated_source_files:
                    data = updated_source_files[info.filename]
                zout.writestr(info, data)

        print(f"Base QDPX: {base_qdpx}")
        print(f"Workspace: {workspace_dir}")
        print(f"Output QDPX: {out_qdpx}")
        print(
            "Applied: "
            f"{renamed} code rename(s), "
            f"{desc_updated} code description update(s), "
            f"{memos_updated} memo text update(s), "
            f"{quote_updates} quotation code reassignment(s)"
        )
        if warnings:
            print(f"Warnings: {len(warnings)}")
            for w in warnings[:20]:
                print(f"- {w}")
            if len(warnings) > 20:
                print(f"- ... {len(warnings) - 20} more")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply qdpx-coding markdown edits back into a QDPX archive.")
    parser.add_argument(
        "--base",
        type=Path,
        default=None,
        help="Base QDPX file to patch. Defaults to newest *.qdpx in workspace root.",
    )
    parser.add_argument(
        "--in",
        dest="in_dir",
        type=Path,
        default=DEFAULT_WORKSPACE,
        help="Input markdown workspace (default: qdpx-coding).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output QDPX path. Defaults to <base-stem>-updated.qdpx",
    )
    args = parser.parse_args()

    base = args.base.resolve() if args.base else _find_default_qdpx().resolve()
    in_dir = args.in_dir.resolve()
    out = args.out.resolve() if args.out else base.with_name(f"{base.stem}-updated{base.suffix}")

    try:
        run_export(base_qdpx=base, workspace_dir=in_dir, out_qdpx=out)
    except CliError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
