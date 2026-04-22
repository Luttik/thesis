#!/usr/bin/env python3
"""qdpx_import.py - Import a QDPX project into a Markdown coding workspace.

Usage:
    python .cursor/skills/qdpx/qdpx_import.py
    python .cursor/skills/qdpx/qdpx_import.py --qdpx "Thesis (...).qdpx"
"""

from __future__ import annotations

import json
import argparse
import re
import sys
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

SKILL_DIR = Path(__file__).parent
WORKSPACE_ROOT = SKILL_DIR.parent.parent.parent
DEFAULT_OUT_DIR = WORKSPACE_ROOT / "qdpx-coding"

QDA_NS = "urn:QDA-XML:project:1.0"
NS = {"q": QDA_NS}


class CliError(Exception):
    """Raised for user-facing CLI input errors."""


@dataclass
class Code:
    guid: str
    name: str
    parent_guid: str | None
    full_name: str
    description: str
    children: list[str] = field(default_factory=list)


@dataclass
class Quote:
    guid: str
    source_guid: str
    source_name: str
    start: int
    end: int
    text: str
    code_guids: list[str]


@dataclass
class SourceDoc:
    guid: str
    name: str
    text: str
    plain_text_path: str
    rich_text_path: str | None
    quotes: list[Quote]


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _slug_filename(name: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]", "_", name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:160] or "untitled"


def _safe_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _iter_code_tree(parent: ET.Element, parent_guid: str | None, prefix: list[str]) -> Iterable[Code]:
    for code_elem in parent.findall("q:Code", NS):
        guid = code_elem.attrib.get("guid", "")
        name = code_elem.attrib.get("name", "(unnamed code)")
        parts = [*prefix, name]
        full_name = ": ".join(parts)

        desc_elem = code_elem.find("q:Description", NS)
        desc = (desc_elem.text or "").strip() if desc_elem is not None else ""

        code = Code(
            guid=guid,
            name=name,
            parent_guid=parent_guid,
            full_name=full_name,
            description=desc,
        )
        yield code
        yield from _iter_code_tree(code_elem, guid, parts)


def _extract_project(zf: zipfile.ZipFile) -> ET.Element:
    try:
        raw = zf.read("project.qde")
    except KeyError as exc:
        raise CliError("QDPX archive does not contain project.qde") from exc
    return ET.fromstring(raw)


def _read_internal_text(zf: zipfile.ZipFile, internal_path: str) -> str:
    rel = internal_path.replace("internal://", "").lstrip("/")
    archive_path = f"sources/{rel}"
    try:
        raw = zf.read(archive_path)
    except KeyError:
        return ""
    return _safe_text(raw.decode("utf-8", errors="replace"))


def _markdown_quote_block(text: str) -> str:
    lines = _safe_text(text).split("\n")
    if not lines:
        return ">"
    return "\n".join(f"> {line}" if line else ">" for line in lines)


def _find_qdpx_default() -> Path:
    candidates = sorted(WORKSPACE_ROOT.glob("*.qdpx"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise CliError("No .qdpx files found in workspace root.")
    return candidates[0]


def run_import(qdpx: Path | None, out: Path) -> None:
    """Import QDPX content into Markdown files for coding and review."""
    qdpx_path = qdpx or _find_qdpx_default()
    qdpx_path = qdpx_path.resolve()
    if not qdpx_path.exists():
        raise CliError(f"QDPX file not found: {qdpx_path}")

    out_dir = out.resolve()
    docs_dir = out_dir / "documents"
    quotes_dir = out_dir / "quotations"
    meta_dir = out_dir / ".meta"
    for p in (docs_dir, quotes_dir, meta_dir):
        p.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []

    with zipfile.ZipFile(qdpx_path, "r") as zf:
        root = _extract_project(zf)

        user_map: dict[str, str] = {}
        for user in root.findall("q:Users/q:User", NS):
            user_map[user.attrib.get("guid", "")] = user.attrib.get("name", "")

        codebook_root = root.find("q:CodeBook/q:Codes", NS)
        if codebook_root is None:
            raise CliError("project.qde does not contain CodeBook/Codes")

        codes: list[Code] = list(_iter_code_tree(codebook_root, parent_guid=None, prefix=[]))
        code_by_guid = {c.guid: c for c in codes if c.guid}
        for c in codes:
            if c.parent_guid and c.parent_guid in code_by_guid:
                code_by_guid[c.parent_guid].children.append(c.guid)

        sources: list[SourceDoc] = []
        source_elems = root.findall("q:Sources/q:TextSource", NS)

        for source_elem in source_elems:
            source_guid = source_elem.attrib.get("guid", "")
            source_name = source_elem.attrib.get("name", "(unnamed source)")
            plain_text_path = source_elem.attrib.get("plainTextPath", "")
            rich_text_path = source_elem.attrib.get("richTextPath")

            text = _read_internal_text(zf, plain_text_path) if plain_text_path else ""
            if not text:
                warnings.append(f"Could not load plain text for source '{source_name}' ({source_guid}).")

            quotes: list[Quote] = []
            for sel in source_elem.findall("q:PlainTextSelection", NS):
                sel_guid = sel.attrib.get("guid", "")
                try:
                    start = int(sel.attrib.get("startPosition", "0"))
                    end = int(sel.attrib.get("endPosition", "0"))
                except ValueError:
                    warnings.append(f"Invalid offsets in selection {sel_guid} ({source_name}).")
                    continue

                if start < 0 or end < start or end > len(text):
                    warnings.append(
                        f"Out-of-bounds selection {sel_guid} in '{source_name}' (start={start}, end={end}, len={len(text)})."
                    )
                    continue

                code_guids: list[str] = []
                for coding in sel.findall("q:Coding", NS):
                    for code_ref in coding.findall("q:CodeRef", NS):
                        target = code_ref.attrib.get("targetGUID", "")
                        if target:
                            code_guids.append(target)

                # Deduplicate while preserving order.
                seen_codes: set[str] = set()
                deduped_codes: list[str] = []
                for cg in code_guids:
                    if cg not in seen_codes:
                        deduped_codes.append(cg)
                        seen_codes.add(cg)

                quote_text = text[start:end].strip("\n")
                quotes.append(
                    Quote(
                        guid=sel_guid,
                        source_guid=source_guid,
                        source_name=source_name,
                        start=start,
                        end=end,
                        text=quote_text,
                        code_guids=deduped_codes,
                    )
                )

            sources.append(
                SourceDoc(
                    guid=source_guid,
                    name=source_name,
                    text=text,
                    plain_text_path=plain_text_path,
                    rich_text_path=rich_text_path,
                    quotes=quotes,
                )
            )

    # Build usage stats and examples.
    code_usage: dict[str, int] = {guid: 0 for guid in code_by_guid}
    code_examples: dict[str, tuple[str, str]] = {}
    for src in sources:
        for q in src.quotes:
            for cg in q.code_guids:
                if cg in code_usage:
                    code_usage[cg] += 1
                    if cg not in code_examples and q.text.strip():
                        snippet = q.text.strip().replace("\n", " ")
                        if len(snippet) > 240:
                            snippet = snippet[:237] + "..."
                        code_examples[cg] = (snippet, src.name)
                else:
                    warnings.append(f"Unknown code GUID referenced in coding: {cg}")

    # Write codebook.md
    imported_local = datetime.now().strftime("%Y-%m-%d %H:%M")
    codebook_lines: list[str] = [
        "# Codebook - QDPX Import",
        f"*Imported {imported_local}*  ",
        f"{len(codes)} codes · {sum(len(s.quotes) for s in sources)} quotations · {len(sources)} documents",
        "",
        "> **Agent instructions**: Read this file first before coding work.",
        "> Edit `Description` fields to refine definitions. Do not edit `<!-- id -->` anchors.",
        "",
        "---",
        "",
    ]

    for code in sorted(codes, key=lambda c: c.full_name.lower()):
        codebook_lines.append(f"## {code.full_name}")
        codebook_lines.append(f"<!-- id: {code.guid} -->")
        if code.parent_guid and code.parent_guid in code_by_guid:
            codebook_lines.append(f"**Parent code**: `{code_by_guid[code.parent_guid].full_name}`  ")
        codebook_lines.append(f"**Used in**: {code_usage.get(code.guid, 0)} quotation(s)  ")
        description = code.description if code.description else "*(not set)*"
        codebook_lines.append(f"**Description**: {description}  ")

        example = code_examples.get(code.guid)
        if example:
            snippet, doc_name = example
            codebook_lines.append("**Example**:")
            codebook_lines.append(f"> {snippet}")
            codebook_lines.append(f"  - *{doc_name}*")
        codebook_lines.append("")

    (out_dir / "codebook.md").write_text("\n".join(codebook_lines).rstrip() + "\n", encoding="utf-8")

    # Write memos.md
    memo_lines: list[str] = [
        "# Memos",
        "",
        "> **Agent instructions**: Edit memo text freely. Do not edit `<!-- id -->` anchors.",
        "",
    ]

    # Notes in QDA-XML map nicely to memos.
    note_elems = root.findall("q:Notes/q:Note", NS) if "root" in locals() else []
    for note in note_elems:
        guid = note.attrib.get("guid", "")
        title = note.attrib.get("name", "(untitled memo)")
        plain_path = note.attrib.get("plainTextPath", "")
        body = ""
        if plain_path:
            with zipfile.ZipFile(qdpx_path, "r") as zf:
                body = _read_internal_text(zf, plain_path).strip()

        memo_lines.append(f"## {title}")
        memo_lines.append(f"<!-- id: {guid} -->")
        memo_lines.append("")
        memo_lines.append(body if body else "*(empty)*")
        memo_lines.append("")
        memo_lines.append("---")
        memo_lines.append("")

    (out_dir / "memos.md").write_text("\n".join(memo_lines).rstrip() + "\n", encoding="utf-8")

    # Write source documents and quotation files.
    for src in sources:
        doc_file = docs_dir / f"{_slug_filename(src.name)}.md"
        doc_lines = [
            f"# Document - {src.name}",
            "",
            f"<!-- id: {src.guid} -->",
            f"<!-- plainTextPath: {src.plain_text_path} -->",
        ]
        if src.rich_text_path:
            doc_lines.append(f"<!-- richTextPath: {src.rich_text_path} -->")
        doc_lines.extend(["", src.text.rstrip(), ""])
        doc_file.write_text("\n".join(doc_lines), encoding="utf-8")

        q_file = quotes_dir / f"{_slug_filename(src.name)}.md"
        q_lines = [
            f"# Quotations - {src.name}",
            "",
            "> **Agent instructions**: Edit the `Codes` line to reassign codes.",
            "> Quoted text (blockquotes) is read-only - boundaries are defined by QDPX offsets.",
            "",
        ]

        sorted_quotes = sorted(src.quotes, key=lambda q: (q.start, q.end, q.guid))
        for i, q in enumerate(sorted_quotes, start=1):
            q_lines.append(f"## Quotation {i}")
            q_lines.append(f"<!-- id: {q.guid} -->")
            q_lines.append(f"<!-- span: {q.start}:{q.end} -->")
            code_names = [code_by_guid[cg].full_name for cg in q.code_guids if cg in code_by_guid]
            codes_md = ", ".join(f"`{name}`" for name in code_names) if code_names else "*(none)*"
            q_lines.append(f"**Codes**: {codes_md}  ")
            q_lines.append("")
            q_lines.append(_markdown_quote_block(q.text))
            q_lines.append("")

        q_file.write_text("\n".join(q_lines).rstrip() + "\n", encoding="utf-8")

    meta = {
        "imported_at_utc": _now_utc(),
        "qdpx_path": str(qdpx_path),
        "output_dir": str(out_dir),
        "documents": len(sources),
        "codes": len(codes),
        "quotations": sum(len(s.quotes) for s in sources),
        "memos": len(note_elems),
        "users": user_map,
        "warnings": warnings,
    }
    (meta_dir / "import.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Imported QDPX: {qdpx_path.name}")
    print(f"Output: {out_dir}")
    print(f"Stats: {meta['codes']} codes, {meta['quotations']} quotations, {meta['documents']} documents")
    if warnings:
        print(f"Warnings: {len(warnings)} (see {meta_dir / 'import.json'})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import QDPX project into Markdown workspace.")
    parser.add_argument(
        "--qdpx",
        type=Path,
        default=None,
        help="Path to .qdpx file. Defaults to newest *.qdpx in workspace root.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Output folder for generated Markdown workspace.",
    )
    args = parser.parse_args()

    try:
        run_import(qdpx=args.qdpx, out=args.out)
    except CliError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
