from docx import Document
from pathlib import Path

d = Document(Path(__file__).resolve().parents[1] / "Thesis Draft - Daan Luttik - MBA.docx")
lines = []
for i, p in enumerate(d.paragraphs):
    if "3.4" in p.text or "Trustworthiness" in p.text or "3.2.1" in p.text:
        lines.append(f"{i}|{p.style.name}|{p.text[:100]}")
Path(__file__).with_name("trust-scan.txt").write_text("\n".join(lines), encoding="utf-8")
