# -*- coding: utf-8 -*-
"""List every em dash (U+2014) in the LIVE (accept-all) text, with context."""
import zipfile
from lxml import etree

DOCX = r"C:\workspace\thesis\Thesis Draft - Daan Luttik - MBA.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
def qn(t): return f"{{{W}}}{t}"
with zipfile.ZipFile(DOCX) as z:
    root = etree.fromstring(z.read("word/document.xml"))

def anc_del(el, stop):
    p = el.getparent()
    while p is not None and p is not stop:
        if etree.QName(p).localname == "del": return True
        p = p.getparent()
    return False
def accept_text(p):
    return "".join(t.text or "" for t in p.iter(qn("t")) if not anc_del(t, p))

total = 0
paras_with = 0
EM = "—"
for i, p in enumerate(root.iter(qn("p"))):
    txt = accept_text(p)
    n = txt.count(EM)
    if n:
        paras_with += 1
        total += n
        print(f"[p{i:04d}] ({n}) {txt.strip()}")
        print("-"*80)
print(f"\nTOTAL em dashes (live): {total} across {paras_with} paragraphs")
