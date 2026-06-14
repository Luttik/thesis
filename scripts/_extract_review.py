#!/usr/bin/env python
"""Extract accepted-changes text from the thesis copy for review.

Produces the 'accept all tracked changes' view: insertions kept inline,
deletions removed. Each paragraph prefixed with index + pStyle.
"""
import zipfile
from lxml import etree

DOCX = r"C:\workspace\thesis\Thesis Draft - Daan Luttik - MBA - copy from 2026-06-14.docx"
OUT = r"C:\workspace\thesis\_review_accepted.txt"

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
def q(tag):
    return f"{{{W}}}{tag}"

with zipfile.ZipFile(DOCX) as z:
    xml = z.read("word/document.xml")

root = etree.fromstring(xml)
body = root.find(q("body"))

def in_deletion(el):
    """True if el is inside a <w:del> ancestor (deleted text)."""
    p = el.getparent()
    while p is not None:
        if etree.QName(p).localname == "del":
            return True
        p = p.getparent()
    return False

lines = []
idx = 0
for p in body.iter(q("p")):
    idx += 1
    style = ""
    pPr = p.find(q("pPr"))
    if pPr is not None:
        ps = pPr.find(q("pStyle"))
        if ps is not None:
            style = ps.get(q("val")) or ""
    parts = []
    for el in p.iter():
        tag = etree.QName(el).localname
        if tag == "t":
            parts.append(el.text or "")
        elif tag == "tab":
            parts.append("\t")
        # delText skipped => accepted view
    text = "".join(parts)
    if text.strip() == "" and style == "":
        continue
    lines.append(f"[{idx:04d}|{style}] {text}")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Wrote {len(lines)} non-empty paragraphs to {OUT}")
