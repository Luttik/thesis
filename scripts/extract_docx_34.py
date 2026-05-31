"""Extract §3.4 trustworthiness content from thesis docx."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".cache" / "docx-section-34.txt"


def main() -> None:
    d = Document(str(ROOT / "Thesis Draft - Daan Luttik - MBA.docx"))
    lines: list[str] = []
    capturing = False
    for child in d.element.body:
        if child.tag.endswith("}p"):
            text = "".join(x.text or "" for x in child.iter(qn("w:t"))).strip()
            if text.startswith("3.4") or ("3.4" in text and "trustworthiness" in text.lower()):
                capturing = True
            if capturing:
                lines.append(f"P: {text}")
                if text.startswith("4.") and "Findings" in text:
                    break
        elif child.tag.endswith("}tbl") and capturing:
            for row in child.findall(".//" + qn("w:tr")):
                cells = row.findall(".//" + qn("w:tc"))
                cell_texts = []
                for tc in cells:
                    cell_texts.append(
                        "".join(x.text or "" for x in tc.iter(qn("w:t"))).strip()
                    )
                lines.append("ROW: " + " || ".join(cell_texts[:2]))
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(lines)} lines")


if __name__ == "__main__":
    main()
