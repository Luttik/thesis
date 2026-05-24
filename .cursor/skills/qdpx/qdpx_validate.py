#!/usr/bin/env python3
"""qdpx_validate.py - Validate QDPX integrity and optional no-loss baseline checks.

Usage:
    python .cursor/skills/qdpx/qdpx_validate.py --qdpx "Thesis.qdpx"
    python .cursor/skills/qdpx/qdpx_validate.py --baseline "before.qdpx" --qdpx "after.qdpx"
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

QDA_NS = "urn:QDA-XML:project:1.0"
NS = {"q": QDA_NS}


class CliError(Exception):
    """Raised for user-facing CLI input errors."""


@dataclass
class Snapshot:
    docs: int
    notes: int
    codes: int
    selections: int
    codings: int
    code_refs: int
    source_guids: set[str]
    note_guids: set[str]


def _load_root(path: Path) -> tuple[zipfile.ZipFile, ET.Element]:
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
    return zf, root


def _snapshot(root: ET.Element) -> Snapshot:
    source_elems = root.findall("q:Sources/q:TextSource", NS)
    note_elems = root.findall("q:Notes/q:Note", NS)
    code_elems = root.findall(".//q:Code", NS)
    selection_elems = root.findall(".//q:PlainTextSelection", NS)
    coding_elems = root.findall(".//q:Coding", NS)
    code_ref_elems = root.findall(".//q:CodeRef", NS)

    source_guids = {
        e.attrib.get("guid", "").upper() for e in source_elems if e.attrib.get("guid", "")
    }
    note_guids = {
        e.attrib.get("guid", "").upper() for e in note_elems if e.attrib.get("guid", "")
    }

    return Snapshot(
        docs=len(source_elems),
        notes=len(note_elems),
        codes=len(code_elems),
        selections=len(selection_elems),
        codings=len(coding_elems),
        code_refs=len(code_ref_elems),
        source_guids=source_guids,
        note_guids=note_guids,
    )


def validate_qdpx(path: Path) -> tuple[Snapshot, list[str], list[str]]:
    zf, root = _load_root(path)
    try:
        errors: list[str] = []
        warnings: list[str] = []

        code_guids = {
            c.attrib.get("guid", "").upper()
            for c in root.findall(".//q:Code", NS)
            if c.attrib.get("guid", "")
        }

        # Source and note text path existence.
        for src in root.findall("q:Sources/q:TextSource", NS):
            name = src.attrib.get("name", "(unnamed source)")
            rel = src.attrib.get("plainTextPath", "").replace("internal://", "").lstrip("/")
            if not rel:
                errors.append(f"Source '{name}' has no plainTextPath.")
                continue
            p = f"sources/{rel}"
            if p not in zf.namelist():
                errors.append(f"Source '{name}' missing text file in archive: {p}")
                continue

            text = zf.read(p).decode("utf-8", errors="replace")
            t_len = len(text)
            for sel in src.findall("q:PlainTextSelection", NS):
                sid = sel.attrib.get("guid", "")
                try:
                    s = int(sel.attrib.get("startPosition", "0"))
                    e = int(sel.attrib.get("endPosition", "0"))
                except ValueError:
                    errors.append(f"Selection {sid} in '{name}' has invalid integer offsets.")
                    continue
                if s < 0 or e < s or e > t_len:
                    errors.append(
                        f"Selection {sid} in '{name}' out of bounds: start={s}, end={e}, text_len={t_len}"
                    )
                if e == s:
                    warnings.append(f"Selection {sid} in '{name}' is zero-length at {s}:{e}.")

        for note in root.findall("q:Notes/q:Note", NS):
            title = note.attrib.get("name", "(untitled note)")
            rel = note.attrib.get("plainTextPath", "").replace("internal://", "").lstrip("/")
            if not rel:
                warnings.append(f"Note '{title}' has no plainTextPath.")
                continue
            p = f"sources/{rel}"
            if p not in zf.namelist():
                errors.append(f"Note '{title}' missing text file in archive: {p}")

        # Orphan code references.
        for ref in root.findall(".//q:CodeRef", NS):
            target = ref.attrib.get("targetGUID", "").upper()
            if target and target not in code_guids:
                errors.append(f"Orphan CodeRef targetGUID not found in CodeBook: {target}")

        return _snapshot(root), errors, warnings
    finally:
        zf.close()


def compare_no_loss(baseline: Snapshot, candidate: Snapshot) -> list[str]:
    errors: list[str] = []

    if candidate.docs < baseline.docs:
        errors.append(f"documents decreased: {baseline.docs} -> {candidate.docs}")
    if candidate.notes < baseline.notes:
        errors.append(f"notes decreased: {baseline.notes} -> {candidate.notes}")
    if candidate.codes < baseline.codes:
        errors.append(f"codes decreased: {baseline.codes} -> {candidate.codes}")
    if candidate.selections < baseline.selections:
        errors.append(f"selections decreased: {baseline.selections} -> {candidate.selections}")
    if candidate.codings < baseline.codings:
        errors.append(f"codings decreased: {baseline.codings} -> {candidate.codings}")
    if candidate.code_refs < baseline.code_refs:
        errors.append(f"code refs decreased: {baseline.code_refs} -> {candidate.code_refs}")

    missing_sources = sorted(baseline.source_guids - candidate.source_guids)
    missing_notes = sorted(baseline.note_guids - candidate.note_guids)
    if missing_sources:
        errors.append(f"source GUIDs missing in candidate: {len(missing_sources)}")
    if missing_notes:
        errors.append(f"note GUIDs missing in candidate: {len(missing_notes)}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate QDPX integrity and no-loss baseline constraints.")
    parser.add_argument("--qdpx", type=Path, required=True, help="Candidate QDPX to validate.")
    parser.add_argument("--baseline", type=Path, default=None, help="Optional baseline QDPX for no-loss checks.")
    args = parser.parse_args()

    try:
        snap, errors, warnings = validate_qdpx(args.qdpx.resolve())
        print(f"Validated: {args.qdpx.resolve()}")
        print(
            "Counts: "
            f"docs={snap.docs}, notes={snap.notes}, codes={snap.codes}, "
            f"selections={snap.selections}, codings={snap.codings}, code_refs={snap.code_refs}"
        )

        if args.baseline is not None:
            base_snap, base_errors, base_warnings = validate_qdpx(args.baseline.resolve())
            if base_errors:
                errors.extend([f"baseline invalid: {e}" for e in base_errors])
            warnings.extend([f"baseline warning: {w}" for w in base_warnings])

            no_loss_errors = compare_no_loss(base_snap, snap)
            errors.extend(no_loss_errors)
            print(
                "Baseline counts: "
                f"docs={base_snap.docs}, notes={base_snap.notes}, codes={base_snap.codes}, "
                f"selections={base_snap.selections}, codings={base_snap.codings}, code_refs={base_snap.code_refs}"
            )

        if warnings:
            print(f"Warnings: {len(warnings)}")
            for w in warnings[:20]:
                print(f"- {w}")
            if len(warnings) > 20:
                print(f"- ... {len(warnings) - 20} more")

        if errors:
            print(f"Errors: {len(errors)}", file=sys.stderr)
            for e in errors[:30]:
                print(f"- {e}", file=sys.stderr)
            if len(errors) > 30:
                print(f"- ... {len(errors) - 30} more", file=sys.stderr)
            raise SystemExit(1)

        print("Validation passed.")
    except CliError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
