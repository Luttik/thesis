from docx import Document
from pathlib import Path

d = Document(Path(__file__).resolve().parents[1] / "Thesis Draft - Daan Luttik - MBA.docx")
lines = []
for i, p in enumerate(d.paragraphs):
    if 105 <= i <= 125 or (280 <= i <= 295) or "3.3" in p.text or "Findings" in p.text:
        lines.append(f"{i}|{p.style.name}|{p.text}")
Path(__file__).resolve().parents[1] / ".cache" / "docx-scan.txt"
out = Path(__file__).resolve().parents[1] / ".cache" / "docx-scan.txt"
out.write_text("\n".join(lines), encoding="utf-8")
print("wrote", out, "lines", len(lines))
