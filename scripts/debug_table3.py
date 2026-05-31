from docx import Document
from pathlib import Path

d = Document(str(Path(__file__).resolve().parents[1] / "Thesis Draft - Daan Luttik - MBA.docx"))
t = d.tables[3]
lines = []
for ri in range(10, 15):
    cells = [c.text.strip() for c in t.rows[ri].cells]
    lines.append(f"{ri}|{cells}")
Path(__file__).resolve().parents[1].joinpath(".cache/table3_debug.txt").write_text(
    "\n".join(lines), encoding="utf-8"
)
