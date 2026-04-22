#!/usr/bin/env python3
"""qdpx_diff.py - Compare two QDPX files (full-project summary + key deltas).

Usage:
    python .cursor/skills/qdpx/qdpx_diff.py --old before.qdpx --new after.qdpx
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

QDA_NS = "urn:QDA-XML:project:1.0"
NS = {"q": QDA_NS}


class CliError(Exception):
    """Raised for user-facing CLI input errors."""


@dataclass
class QdpxStats:
    docs: int
    notes: int
    codes: int
    selections: int
    codings: int
    code_refs: int
    per_doc_selections: dict[str, int]
    per_doc_codings: dict[str, int]
    code_usage: Counter[str]


def _load(path: Path) -> ET.Element:
    try:
        with zipfile.ZipFile(path, "r") as zf:
            return ET.fromstring(zf.read("project.qde"))
    except FileNotFoundError as exc:
        raise CliError(f"QDPX not found: {path}") from exc
    except zipfile.BadZipFile as exc:
        raise CliError(f"Invalid zip/QDPX file: {path}") from exc
    except KeyError as exc:
        raise CliError(f"QDPX missing project.qde: {path}") from exc


def _code_guid_to_name(root: ET.Element) -> dict[str, str]:
    out: dict[str, str] = {}

    def walk(parent: ET.Element, prefix: list[str]) -> None:
        for c in parent.findall("q:Code", NS):
            name = c.attrib.get("name", "")
            guid = c.attrib.get("guid", "").upper()
            full = ": ".join(prefix + [name]) if prefix else name
            if guid:
                out[guid] = full
            walk(c, prefix + [name])

    codes_root = root.find("q:CodeBook/q:Codes", NS)
    if codes_root is not None:
        walk(codes_root, [])
    return out


def _stats(root: ET.Element) -> QdpxStats:
    code_name = _code_guid_to_name(root)

    docs = root.findall("q:Sources/q:TextSource", NS)
    notes = root.findall("q:Notes/q:Note", NS)
    codes = root.findall(".//q:Code", NS)
    sels = root.findall(".//q:PlainTextSelection", NS)
    codings = root.findall(".//q:Coding", NS)
    refs = root.findall(".//q:CodeRef", NS)

    per_doc_sel: dict[str, int] = {}
    per_doc_coding: dict[str, int] = {}
    code_usage: Counter[str] = Counter()

    for doc in docs:
        name = doc.attrib.get("name", "(unnamed source)")
        doc_sels = doc.findall("q:PlainTextSelection", NS)
        per_doc_sel[name] = len(doc_sels)

        coding_count = 0
        for sel in doc_sels:
            for coding in sel.findall("q:Coding", NS):
                coding_count += 1
                for ref in coding.findall("q:CodeRef", NS):
                    tgt = ref.attrib.get("targetGUID", "").upper()
                    if not tgt:
                        continue
                    code_usage[code_name.get(tgt, f"UNKNOWN:{tgt}")] += 1
        per_doc_coding[name] = coding_count

    return QdpxStats(
        docs=len(docs),
        notes=len(notes),
        codes=len(codes),
        selections=len(sels),
        codings=len(codings),
        code_refs=len(refs),
        per_doc_selections=per_doc_sel,
        per_doc_codings=per_doc_coding,
        code_usage=code_usage,
    )


def _print_count_delta(label: str, old: int, new: int) -> None:
    delta = new - old
    sign = "+" if delta > 0 else ""
    print(f"- {label}: {old} -> {new} ({sign}{delta})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two QDPX files and print key deltas.")
    parser.add_argument("--old", type=Path, required=True, help="Baseline/original QDPX")
    parser.add_argument("--new", type=Path, required=True, help="Candidate/updated QDPX")
    args = parser.parse_args()

    try:
        old_root = _load(args.old.resolve())
        new_root = _load(args.new.resolve())
    except CliError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    old = _stats(old_root)
    new = _stats(new_root)

    print("QDPX Diff Report")
    print(f"- Old: {args.old.resolve()}")
    print(f"- New: {args.new.resolve()}")
    _print_count_delta("documents", old.docs, new.docs)
    _print_count_delta("notes", old.notes, new.notes)
    _print_count_delta("codes", old.codes, new.codes)
    _print_count_delta("selections", old.selections, new.selections)
    _print_count_delta("codings", old.codings, new.codings)
    _print_count_delta("code refs", old.code_refs, new.code_refs)

    print("\nPer-document selection deltas (top 12 by absolute delta)")
    all_docs = sorted(set(old.per_doc_selections) | set(new.per_doc_selections))
    doc_deltas = []
    for name in all_docs:
        o = old.per_doc_selections.get(name, 0)
        n = new.per_doc_selections.get(name, 0)
        d = n - o
        if d != 0:
            doc_deltas.append((abs(d), name, o, n, d))
    for _absd, name, o, n, d in sorted(doc_deltas, reverse=True)[:12]:
        sign = "+" if d > 0 else ""
        print(f"- {name}: {o} -> {n} ({sign}{d})")
    if not doc_deltas:
        print("- (no selection count changes)")

    print("\nPer-document coding deltas (top 12 by absolute delta)")
    all_docs = sorted(set(old.per_doc_codings) | set(new.per_doc_codings))
    coding_deltas = []
    for name in all_docs:
        o = old.per_doc_codings.get(name, 0)
        n = new.per_doc_codings.get(name, 0)
        d = n - o
        if d != 0:
            coding_deltas.append((abs(d), name, o, n, d))
    for _absd, name, o, n, d in sorted(coding_deltas, reverse=True)[:12]:
        sign = "+" if d > 0 else ""
        print(f"- {name}: {o} -> {n} ({sign}{d})")
    if not coding_deltas:
        print("- (no coding count changes)")

    print("\nCode usage deltas (top 20 by absolute delta)")
    all_codes = sorted(set(old.code_usage) | set(new.code_usage))
    usage_deltas = []
    for code in all_codes:
        o = old.code_usage.get(code, 0)
        n = new.code_usage.get(code, 0)
        d = n - o
        if d != 0:
            usage_deltas.append((abs(d), code, o, n, d))
    for _absd, code, o, n, d in sorted(usage_deltas, reverse=True)[:20]:
        sign = "+" if d > 0 else ""
        print(f"- {code}: {o} -> {n} ({sign}{d})")
    if not usage_deltas:
        print("- (no code usage changes)")


if __name__ == "__main__":
    main()
