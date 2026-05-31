from docx import Document
from pathlib import Path

d = Document(Path(__file__).resolve().parents[1] / "Thesis Draft - Daan Luttik - MBA.docx")
lines = [f"{i}|{p.style.name}|{p.text}" for i, p in enumerate(d.paragraphs) if 120 <= i <= 145]
Path(__file__).with_name("trust-range.txt").write_text("\n".join(lines), encoding="utf-8")
