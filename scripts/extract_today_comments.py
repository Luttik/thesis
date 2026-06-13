# -*- coding: utf-8 -*-
"""Extract comments dated 2026-06-13 from the SBcomments docx: author, the
heading they sit under, the anchored text span, and the comment body."""
import zipfile
from lxml import etree

DOCX = r"C:\workspace\thesis\NEW - Thesis Draft - Daan Luttik - MBA - SBcomments.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W15 = "http://schemas.microsoft.com/office/word/2012/wordml"
def q(t): return f"{{{W}}}{t}"
DATE = "2026-06-13"

z = zipfile.ZipFile(DOCX)
cx = etree.fromstring(z.read("word/comments.xml"))
comments = {}
for c in cx.findall(q("comment")):
    cid = c.get(q("id"))
    # comment body as paragraphs
    paras = []
    for p in c.findall(q("p")):
        paras.append("".join(t.text or "" for t in p.iter(q("t"))))
    comments[cid] = {"author": c.get(q("author")), "date": (c.get(q("date")) or "")[:10],
                     "text": "\n".join(x for x in paras if x).strip()}

# threading: commentsExtended maps paraId -> parent paraId; map comment paraId
try:
    ce = etree.fromstring(z.read("word/commentsExtended.xml"))
    W15ns = "{%s}" % W15
    para_parent = {}
    for el in ce.iter(W15ns + "commentEx"):
        pid = el.get(W15ns + "paraId"); par = el.get(W15ns + "paraIdParent")
        para_parent[pid] = par
    # map each comment's first para paraId
    cid_para = {}
    for c in cx.findall(q("comment")):
        p0 = c.find(q("p"))
        if p0 is not None:
            cid_para[c.get(q("id"))] = p0.get("{http://schemas.microsoft.com/office/word/2010/wordml}paraId")
    para_to_cid = {v: k for k, v in cid_para.items()}
    for cid, pid in cid_para.items():
        par = para_parent.get(pid)
        comments[cid]["reply_to"] = para_to_cid.get(par) if par else None
except Exception as e:
    pass

# walk document.xml: capture anchored text per comment id, track current headings
doc = etree.fromstring(z.read("word/document.xml"))
body = doc.find(q("body"))
active = {}      # id -> list of chars
anchored = {}
h1 = h2 = h3 = ""
def ptext(p): return "".join(t.text or "" for t in p.iter(q("t")))
for el in body.iter():
    tag = etree.QName(el).localname
    if tag == "p" and el.getparent().tag == q("body"):
        pPr = el.find(q("pPr")); sty = ""
        if pPr is not None:
            ps = pPr.find(q("pStyle"))
            if ps is not None: sty = ps.get(q("val")) or ""
        if sty == "Heading1": h1 = ptext(el); h2 = h3 = ""
        elif sty == "Heading2": h2 = ptext(el); h3 = ""
        elif sty == "Heading3": h3 = ptext(el)
    if tag == "commentRangeStart":
        cid = el.get(q("id")); active[cid] = []; anchored.setdefault(cid, {"loc": f"{h1[:18]} > {h2[:24]} > {h3[:26]}"})
    elif tag == "commentRangeEnd":
        active.pop(el.get(q("id")), None)
    elif tag == "t":
        for cid in active: active[cid].append(el.text or "")
for cid, lst in {**{k: [] for k in anchored}}.items():
    pass
# join anchored text captured incrementally
acc = {}
active = {}
h1 = h2 = h3 = ""
for el in body.iter():
    tag = etree.QName(el).localname
    if tag == "p" and el.getparent().tag == q("body"):
        pPr = el.find(q("pPr")); sty = ""
        if pPr is not None:
            ps = pPr.find(q("pStyle"))
            if ps is not None: sty = ps.get(q("val")) or ""
        if sty == "Heading1": h1 = ptext(el)
        elif sty == "Heading2": h2 = ptext(el)
        elif sty == "Heading3": h3 = ptext(el)
    if tag == "commentRangeStart":
        cid = el.get(q("id")); active[cid] = True; acc.setdefault(cid, ["", f"{h1[:16]}>{h2[:20]}>{h3[:24]}"])
        acc[cid][1] = f"{h1[:16]}>{h2[:20]}>{h3[:24]}"
    elif tag == "commentRangeEnd":
        active.pop(el.get(q("id")), None)
    elif tag == "t":
        for cid in list(active): acc[cid][0] += (el.text or "")

# output today's comments
today = [(cid, c) for cid, c in comments.items() if c["date"] == DATE]
print(f"=== {len(today)} comments dated {DATE} ===\n")
for cid, c in sorted(today, key=lambda x: int(x[0])):
    anc, loc = acc.get(cid, ["<no anchor>", "?"])
    reply = c.get("reply_to")
    rflag = f"  (reply to #{reply})" if reply else ""
    print(f"#{cid} · {c['author']}{rflag}\n  loc: {loc}\n  anchored: \"{anc.strip()[:200]}\"\n  COMMENT: {c['text'][:400]}\n")
