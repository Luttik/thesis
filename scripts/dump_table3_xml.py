from pathlib import Path
from docx import Document
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
FN = "Thesis Draft - Daan Luttik - MBA - copy from 2026-06-14.docx"
d = Document(str(ROOT / FN))

for ti in (2, 3):
    t = d.tables[ti]
    xml = etree.tostring(t._tbl, pretty_print=True).decode("utf-8")
    (ROOT / ".cache" / f"table{ti}_raw.xml").write_text(xml, encoding="utf-8")
    print(f"table #{ti}: {len(xml)} chars -> .cache/table{ti}_raw.xml")
