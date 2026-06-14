#!/usr/bin/env python
"""Inspect structural anomalies in the thesis copy:
 - heading paragraphs whose accepted text is empty/very short
 - any Word 'move' tracked changes (moveFrom/moveTo)
 - raw run breakdown (ins/del) for a chosen set of paragraph indices
"""
import zipfile
from lxml import etree

DOCX = r"C:\workspace\thesis\Thesis Draft - Daan Luttik - MBA - copy from 2026-06-14.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
def q(tag): return f"{{{W}}}{tag}"

with zipfile.ZipFile(DOCX) as z:
    xml = z.read("word/document.xml")
root = etree.fromstring(xml)
body = root.find(q("body"))

# global scan for move markers
move_tags = ["moveFrom","moveTo","moveFromRangeStart","moveToRangeStart"]
print("=== MOVE markers in document ===")
found_move = False
for t in move_tags:
    els = root.findall(".//"+q(t))
    if els:
        found_move = True
        print(f"  {t}: {len(els)} occurrences")
if not found_move:
    print("  (none)")

# enumerate paragraphs, index matches extractor (body.iter('p'))
paras = list(body.iter(q("p")))
def accepted_text(p):
    parts=[]
    for el in p.iter():
        tag=etree.QName(el).localname
        if tag=="t": parts.append(el.text or "")
        elif tag=="tab": parts.append("\t")
    return "".join(parts)
def style(p):
    pPr=p.find(q("pPr"))
    if pPr is not None:
        ps=pPr.find(q("pStyle"))
        if ps is not None: return ps.get(q("val")) or ""
    return ""

print("\n=== Heading paragraphs with EMPTY/short accepted text ===")
idx=0
for p in paras:
    idx+=1
    st=style(p)
    if st.startswith("Heading") or st in ("TOCHeading",):
        txt=accepted_text(p).strip()
        if len(txt)<=3:
            print(f"  [{idx:04d}|{st}] accepted=>{txt!r}")

print("\n=== Raw run/ins/del breakdown for selected paragraphs ===")
TARGETS={593,599,600,601,602,605,612,613,618,619,620,621,
         494,495,496, 109,110,111, 556,557,558,559,560,561,562,563,564,
         545,546,547}
idx=0
for p in paras:
    idx+=1
    if idx not in TARGETS: continue
    st=style(p)
    print(f"\n--- [{idx:04d}|{st}] ---")
    # walk children to show ins/del structure
    def walk(el, depth=0):
        tag=etree.QName(el).localname
        if tag in ("ins","del","moveFrom","moveTo"):
            author=el.get(q("author"))
            print("   "*depth + f"<{tag} author={author}>")
            for c in el: walk(c, depth+1)
        elif tag=="r":
            txt=""
            for c in el:
                ct=etree.QName(c).localname
                if ct=="t": txt+=(c.text or "")
                elif ct=="delText": txt+="<DEL:"+(c.text or "")+">"
                elif ct=="tab": txt+="\\t"
            print("   "*depth + f"r: {txt!r}")
        elif tag=="hyperlink":
            print("   "*depth + "<hyperlink>")
            for c in el: walk(c, depth+1)
        else:
            for c in el: walk(c, depth)
    walk(p)
