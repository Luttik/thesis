from pathlib import Path
from docx import Document

ROOT = Path(__file__).resolve().parents[1]
FN = "Thesis Draft - Daan Luttik - MBA - copy from 2026-06-14.docx"
d = Document(str(ROOT / FN))

out = []
for ti in (2, 3):
    t = d.tables[ti]
    out.append(f"################ TABLE #{ti}  rows={len(t.rows)} cols={len(t.columns)} ################")
    for ri, row in enumerate(t.rows):
        cells = row.cells
        for ci, c in enumerate(cells):
            txt = c.text.replace("\n", " \\n ")
            out.append(f"[{ti}] r{ri} c{ci}: {txt}")
        out.append("  ----")
    out.append("")

(ROOT / ".cache" / "table3_both.txt").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
