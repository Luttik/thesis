#!/usr/bin/env python
"""Dump run/ins/del structure for paragraphs containing given anchor strings,
so we can choose a safe tracked-change strategy."""
import zipfile
from lxml import etree

DOCX = r"C:\workspace\thesis\Thesis Draft - Daan Luttik - MBA - copy from 2026-06-14.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
def q(t): return f"{{{W}}}{t}"

ANCHORS = [
    "are present in are described by",
    "various different forms and notes how",
    "Moralles et al. (2026) notes",
    "Enholm et al (2022) and Holmström",
    "in bulk. is the benefit",
    "Vaid et al (2025) note",
    "AID-SMJ882",
]

with zipfile.ZipFile(DOCX) as z:
    root = etree.fromstring(z.read("word/document.xml"))
body = root.find(q("body"))

def visible_text(p):
    out=[]
    for t in p.iter(q("t")):
        anc=t.getparent(); indel=False
        while anc is not None:
            if anc.tag==q("del"): indel=True; break
            anc=anc.getparent()
        if not indel: out.append(t.text or "")
    return "".join(out)

for anchor in ANCHORS:
    print(f"\n===== ANCHOR: {anchor!r} =====")
    found=False
    for p in body.iter(q("p")):
        if anchor in visible_text(p):
            found=True
            for r in p.findall(q("r")):  # direct-child runs only
                t=r.find(q("t"))
                txt=t.text if t is not None else None
                # mark short
                disp = (txt[:60]+"…") if txt and len(txt)>60 else txt
                print(f"   direct w:r  t={disp!r}")
            # any runs nested in ins/del?
            n_ins=len(p.findall(".//"+q("ins")))
            n_del=len(p.findall(".//"+q("del")))
            n_hyper=len(p.findall(".//"+q("hyperlink")))
            print(f"   [nested ins={n_ins} del={n_del} hyperlink={n_hyper}; direct runs={len(p.findall(q('r')))}]")
            break
    if not found:
        print("   (anchor not found)")
