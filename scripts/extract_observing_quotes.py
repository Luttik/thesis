#!/usr/bin/env python3
"""Extract QDPX quotes for observing-section artifact codes."""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

QDA_NS = "urn:QDA-XML:project:1.0"
NS = {"q": QDA_NS}
WORKSPACE = Path(__file__).resolve().parents[1]
QDPX = WORKSPACE / "qdpx" / "Thesis (Daan Luttik 2026-05-30).qdpx"

TARGET_CODES = [
    "Leveraging external experts",
    "advisor / consultant",
    "Following vendors' AI strategy",
    "Multiple vendors / solutions",
    "One key vendor",
]

NAME_HINTS = [
    "Andreea",
    "Arjan",
    "Berfun",
    "Dennis",
    "Erik",
    "Erica",
    "Georgio",
    "Jon",
    "Lauren",
    "Maarten",
    "Rolf",
    "Scott",
    "Tim",
    "Floris",
    "Sylvia",
    "Karin",
]


def interviewee_num(source_name: str) -> int | None:
    match = re.search(r"Interview(?:ee)?\s*(\d+)", source_name, re.I)
    if match:
        return int(match.group(1))
    lowered = source_name.lower()
    for index, hint in enumerate(NAME_HINTS, start=1):
        if hint.lower() in lowered:
            return index
    return None


def read_source_text(zf: zipfile.ZipFile, plain_text_path: str) -> str:
    rel = plain_text_path.replace("internal://", "").lstrip("/")
    return zf.read(f"sources/{rel}").decode("utf-8", errors="replace")


def main() -> None:
    with zipfile.ZipFile(QDPX) as zf:
        root = ET.fromstring(zf.read("project.qde"))
        codebook = root.find("q:CodeBook/q:Codes", NS)
        if codebook is None:
            raise SystemExit("No codebook found")

        codes: dict[str, str] = {}

        def walk(elem: ET.Element) -> None:
            for code_elem in elem.findall("q:Code", NS):
                guid = code_elem.get("guid", "")
                name = code_elem.get("name", "")
                if guid:
                    codes[guid] = name
                walk(code_elem)

        walk(codebook)
        name_to_guid = {name: guid for guid, name in codes.items()}
        target_guids = {name_to_guid[name] for name in TARGET_CODES if name in name_to_guid}

        results: dict[str, list[dict[str, object]]] = {
            name: [] for name in TARGET_CODES if name in name_to_guid
        }

        for source in root.findall("q:Sources/q:TextSource", NS):
            source_name = source.get("name", "")
            text = read_source_text(zf, source.get("plainTextPath", ""))
            for selection in source.findall("q:PlainTextSelection", NS):
                code_names: list[str] = []
                for coding in selection.findall("q:Coding", NS):
                    for code_ref in coding.findall("q:CodeRef", NS):
                        target = code_ref.get("targetGUID", "")
                        if target in target_guids:
                            code_names.append(codes[target])
                if not code_names:
                    continue

                start = int(selection.get("startPosition", "0"))
                end = int(selection.get("endPosition", "0"))
                quote_text = re.sub(r"\s+", " ", text[start:end].strip())
                entry = {
                    "text": quote_text,
                    "source": source_name,
                    "codes": sorted(set(code_names)),
                    "int": interviewee_num(source_name),
                }
                for code_name in set(code_names):
                    if code_name in results:
                        results[code_name].append(entry)

    out = WORKSPACE / ".cache" / "observing_quotes_extract.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")

    for code_name, quotes in results.items():
        print(f"\n=== {code_name} ({len(quotes)}) ===")
        for quote in quotes:
            num = quote["int"]
            label = f"I{num}" if num else "?"
            snippet = str(quote["text"])[:220]
            print(f"  {label} | {snippet}")


if __name__ == "__main__":
    main()
