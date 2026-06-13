# -*- coding: utf-8 -*-
"""Verify the methodology-table + chapter-5 patches: simulate accept-all and
reject-all, check tables/captions/cross-refs, and scan for duplicate change ids."""
import zipfile, copy, re
from lxml import etree

DOCX = r"C:\workspace\thesis\Thesis Draft - Daan Luttik - MBA - copy from 2026-06-13.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
def q(t): return f"{{{W}}}{t}"
XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"

xml = zipfile.ZipFile(DOCX).read("word/document.xml")
root0 = etree.fromstring(xml)

# duplicate-id scan
ids = [el.get(q("id")) for el in root0.iter() if el.tag in (q("ins"), q("del")) and el.get(q("id"))]
dups = {i for i in ids if ids.count(i) > 1}
print(f"change marks: {len(ids)}; duplicate ids: {sorted(dups) if dups else 'none'}")

def transform(root, accept):
    # row-level marks
    for tr in list(root.iter(q("tr"))):
        trPr = tr.find(q("trPr"))
        if trPr is None: continue
        ins = trPr.find(q("ins")); dele = trPr.find(q("del"))
        if accept:
            if dele is not None: tr.getparent().remove(tr); continue
            if ins is not None: trPr.remove(ins)
        else:
            if ins is not None: tr.getparent().remove(tr); continue
            if dele is not None: trPr.remove(dele)
    # paragraph-mark marks
    for rPr in list(root.iter(q("rPr"))):
        if rPr.getparent() is not None and rPr.getparent().tag == q("pPr"):
            for m in rPr.findall(q("ins")) + rPr.findall(q("del")):
                rPr.remove(m)
    # run-level ins
    for ins in list(root.iter(q("ins"))):
        par = ins.getparent()
        if par is None or par.tag == q("trPr"): continue
        if accept:
            i = list(par).index(ins)
            for j, ch in enumerate(list(ins)): par.insert(i + j, ch)
        par.remove(ins)
    # run-level del
    for d in list(root.iter(q("del"))):
        par = d.getparent()
        if par is None or par.tag == q("trPr"): continue
        if accept:
            par.remove(d)
        else:
            for dt in d.iter(q("delText")):
                t = etree.Element(q("t")); t.set(XMLSPACE, "preserve"); t.text = dt.text
                dt.getparent().replace(dt, t)
            i = list(par).index(d)
            for j, ch in enumerate(list(d)): par.insert(i + j, ch)
            par.remove(d)
    # drop tables emptied by row deletion (mimic Word)
    for tbl in list(root.iter(q("tbl"))):
        if not tbl.findall(q("tr")):
            tbl.getparent().remove(tbl)
    return root

def ptext(p): return "".join(t.text or "" for t in p.iter(q("t")))

def report(label, root):
    body = root.find(q("body"))
    print(f"\n===== {label} =====")
    tbls = [el for el in body.iter(q("tbl")) if el.getparent().tag == q("body")]
    for n, t in enumerate(tbls, 1):
        rows = t.findall(q("tr"))
        head = " | ".join("".join(x.text or "" for x in tc.iter(q("t"))) for tc in rows[0].findall(q("tc"))) if rows else ""
        print(f"  table {n}: {len(rows)} rows | head: {head[:55]}")
    caps = [ptext(p).strip() for p in body.iter(q("p")) if ptext(p).strip() in ("Table 4", "Table 5") ]
    print(f"  Table4/5 captions present: {caps}")

acc = transform(copy.deepcopy(root0), True)
rej = transform(copy.deepcopy(root0), False)
report("ACCEPT ALL", acc)
report("REJECT ALL", rej)

# coding table content after accept (the realigned one)
body = acc.find(q("body"))
for t in body.iter(q("tbl")):
    rows = t.findall(q("tr"))
    h = "".join(x.text or "" for x in rows[0].iter(q("t"))) if rows else ""
    if "Open coding" in h:
        print("\n--- realigned coding table (ACCEPT) ---")
        for r in rows:
            cells = [" ".join("".join(x.text or "" for x in p.iter(q("t"))) for p in tc.findall(q("p"))) for tc in r.findall(q("tc"))]
            print("   |", " || ".join(c[:48] for c in cells))
        break

# ch5 cross-ref sanity after accept
print("\n--- chapter 5 cross-ref sanity (ACCEPT) ---")
bad = []
for p in body.iter(q("p")):
    s = ptext(p)
    for pat in ["4.5.", "4.4.4", "4.2.4", "4.1.3"]:
        if pat in s:
            bad.append((pat, s[max(0, s.find(pat)-25):s.find(pat)+8]))
print("  stale refs remaining:", bad if bad else "none")
heads = [ptext(p).strip()[:40] for p in body.iter(q("p"))
         if re.match(r"5\.1\.[234]\b", ptext(p).strip())]
print("  §5.1 numbered headings:", heads)
