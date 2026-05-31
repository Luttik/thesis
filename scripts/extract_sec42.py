"""Extract paragraph text by index range."""

from __future__ import annotations

from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
doc = Document(str(ROOT / "Thesis Draft - Daan Luttik - MBA.docx"))
lines = []
for i in range(127, 215):
    p = doc.paragraphs[i]
    lines.append(f"=== {i} {p.style.name} ===")
    lines.append(p.text)
    lines.append("")
(ROOT / ".cache" / "sec42_extract.txt").write_text("\n".join(lines), encoding="utf-8")
