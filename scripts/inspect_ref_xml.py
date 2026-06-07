# -*- coding: utf-8 -*-
"""Dump the XML of selected paragraphs so new entries can match formatting."""
import zipfile
from lxml import etree

DOCX = r"C:\workspace\thesis\Thesis Draft - Daan Luttik - MBA.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
def qn(t): return f"{{{W}}}{t}"

with zipfile.ZipFile(DOCX) as z:
    root = etree.fromstring(z.read("word/document.xml"))

def full_text(p):
    return "".join(t.text or "" for t in p.iter(qn("t")))

markers = [
    "Dynamic capabilities and strategic management",   # Teece 1997 ref
    "Value creation and value capture",                # Lepak 2007 ref
]
for p in root.iter(qn("p")):
    txt = full_text(p)
    for m in markers:
        if m in txt:
            print("=" * 80)
            print("MARKER:", m)
            print(etree.tostring(p, pretty_print=True).decode("utf-8"))
            break
