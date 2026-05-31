"""Scan methodology chapter paragraphs."""

from __future__ import annotations

from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".cache" / "para-methodology.txt"


def main() -> None:
    d = Document(str(ROOT / "Thesis Draft - Daan Luttik - MBA.docx"))
    lines: list[str] = []
    capture = False
    for i, p in enumerate(d.paragraphs):
        t = p.text.strip()
        if t.startswith("3.") or t.startswith("4."):
            capture = True
        if capture:
            if t.startswith("5.") or (t.startswith("4.") and "Discussion" in t):
                break
            if t or p.style.name.startswith("Heading"):
                lines.append(f"{i}|{p.style.name}|{t[:100]}")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"lines: {len(lines)}")


if __name__ == "__main__":
    main()
