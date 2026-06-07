#!/usr/bin/env python
"""Extract paragraph text from the thesis DOCX, including tracked changes.

Renders inserted text inline, marks deleted text as <<DEL:...>>, and prefixes
each paragraph with its index and pStyle so sections can be located precisely.
"""
import sys
import zipfile
from lxml import etree

DOCX = r"C:\workspace\thesis\Thesis Draft - Daan Luttik - MBA.docx"
OUT = r"C:\workspace\thesis\_extract_tmp.txt"

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
def q(tag):
    return f"{{{W}}}{tag}"

with zipfile.ZipFile(DOCX) as z:
    xml = z.read("word/document.xml")

root = etree.fromstring(xml)
body = root.find(q("body"))

lines = []
idx = 0
for p in body.iter(q("p")):
    idx += 1
    # style
    style = ""
    pPr = p.find(q("pPr"))
    if pPr is not None:
        ps = pPr.find(q("pStyle"))
        if ps is not None:
            style = ps.get(q("val")) or ""
    # reconstruct text
    parts = []
    for el in p.iter():
        tag = etree.QName(el).localname
        if tag == "t":
            parts.append(el.text or "")
        elif tag == "delText":
            parts.append(f"<<DEL:{el.text or ''}>>")
        elif tag == "tab":
            parts.append("\t")
    text = "".join(parts)
    if text.strip() == "" and style == "":
        continue
    lines.append(f"[{idx:04d}|{style}] {text}")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Wrote {len(lines)} non-empty paragraphs to {OUT}")
