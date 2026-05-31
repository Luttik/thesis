from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
d = Document(str(ROOT / "Thesis Draft - Daan Luttik - MBA.docx"))
t = d.tables[3]
lines = [f"rows={len(t.rows)} cols={len(t.columns)}"]
for ri, row in enumerate(t.rows):
    lines.append(f"{ri}|" + "|".join(c.text.replace("\n", " ")[:60] for c in row.cells))
(ROOT / ".cache" / "table3.txt").write_text("\n".join(lines), encoding="utf-8")
print("done", len(lines))
