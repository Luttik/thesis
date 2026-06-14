from pathlib import Path
from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
FN = "Thesis Draft - Daan Luttik - MBA - copy from 2026-06-14.docx"
d = Document(str(ROOT / FN))

out = []
out.append(f"total tables = {len(d.tables)}")

# Map each table element to find the paragraph caption preceding it.
body = d.element.body
# Build an ordered list of block elements (paragraphs + tables)
children = list(body.iterchildren())

# For caption detection, walk the body and remember last paragraph text before each tbl
last_paras = []
tbl_index = 0
for el in children:
    if el.tag == qn("w:p"):
        # get text
        texts = el.findall(".//" + qn("w:t"))
        txt = "".join(t.text or "" for t in texts)
        last_paras.append(txt)
        if len(last_paras) > 4:
            last_paras.pop(0)
    elif el.tag == qn("w:tbl"):
        out.append("")
        out.append(f"==== TABLE #{tbl_index} ====")
        out.append("  preceding paras: " + " || ".join(p[:70] for p in last_paras if p.strip()))
        tbl_index += 1

(ROOT / ".cache").mkdir(exist_ok=True)
(ROOT / ".cache" / "copy_tables_overview.txt").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
