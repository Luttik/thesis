# -*- coding: utf-8 -*-
"""Address Stefanie Beninger's 2026-06-13 comments — the clear, mechanical ones
(tracked, author 'Claude'). Substantive rewrites (#135 Figure 1, #247 table
integration) are handled separately after review."""
from __future__ import annotations
import copy, shutil, sys
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

DOCX = Path(__file__).resolve().parents[1] / "Thesis Draft - Daan Luttik - MBA - copy from 2026-06-13.docx"
BACKUP = DOCX.with_suffix(".sbcomments-backup.docx")
AUTHOR = "Claude"; DATE = "2026-06-13T17:40:00Z"
XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"
APO = "’"  # curly apostrophe
RDQ = "”"

def _used(doc): return {int(el.get(qn("w:id"), 0)) for el in doc.element.body.iter() if el.get(qn("w:id")) is not None}
def _nid(u): n = max(u, default=0) + 1; u.add(n); return n
def full_text(p): return "".join(t.text or "" for t in p.iter(qn("w:t")))
def find_elem(doc, m):
    for p in doc.paragraphs:
        if m in full_text(p._element): return p._element
    return None

def _mkrun(rPr, s):
    r = etree.Element(qn("w:r"))
    if rPr is not None: r.append(copy.deepcopy(rPr))
    t = etree.SubElement(r, qn("w:t")); t.set(XMLSPACE, "preserve"); t.text = s
    return r
def _insrun(s, u):
    ins = etree.Element(qn("w:ins")); ins.set(qn("w:id"), str(_nid(u)))
    ins.set(qn("w:author"), AUTHOR); ins.set(qn("w:date"), DATE)
    r = etree.SubElement(ins, qn("w:r")); t = etree.SubElement(r, qn("w:t"))
    t.set(XMLSPACE, "preserve"); t.text = s
    return ins

def replace_fragment(p, old, new, u):
    runs = p.findall(qn("w:r")); segs = []; total = ""
    for r in runs:
        t = r.find(qn("w:t")); txt = t.text if (t is not None and t.text) else ""
        segs.append((r, txt)); total += txt
    start = total.find(old)
    if start < 0: return False
    end = start + len(old)
    def mk_del(rPr, s):
        d = etree.Element(qn("w:del")); d.set(qn("w:id"), str(_nid(u)))
        d.set(qn("w:author"), AUTHOR); d.set(qn("w:date"), DATE)
        dr = etree.SubElement(d, qn("w:r"))
        if rPr is not None: dr.insert(0, copy.deepcopy(rPr))
        dt = etree.SubElement(dr, qn("w:delText")); dt.set(XMLSPACE, "preserve"); dt.text = s
        return d
    pos, inserted = 0, False
    for r, txt in segs:
        rs, re_ = pos, pos + len(txt); pos = re_
        if not txt or re_ <= start or rs >= end: continue
        rPr = r.find(qn("w:rPr"))
        ls = max(start, rs) - rs; le = min(end, re_) - rs
        before, deleted, after = txt[:ls], txt[ls:le], txt[le:]
        parent = r.getparent(); idx = list(parent).index(r); parts = []
        if before: parts.append(_mkrun(rPr, before))
        if not inserted and new: parts.append(_insrun(new, u)); inserted = True
        elif not inserted: inserted = True
        if deleted: parts.append(mk_del(rPr, deleted))
        if after: parts.append(_mkrun(rPr, after))
        for j, pt in enumerate(parts): parent.insert(idx + j, pt)
        parent.remove(r)
    return True

def insert_after(p, anchor, new_text, u):
    runs = p.findall(qn("w:r")); segs = []; total = ""
    for r in runs:
        t = r.find(qn("w:t")); txt = t.text if (t is not None and t.text) else ""
        segs.append((r, txt)); total += txt
    pos = total.find(anchor)
    if pos < 0: return False
    end = pos + len(anchor); cur = 0
    for r, txt in segs:
        rs, re_ = cur, cur + len(txt); cur = re_
        if txt and rs < end <= re_:
            off = end - rs; before, after = txt[:off], txt[off:]
            rPr = r.find(qn("w:rPr")); parent = r.getparent(); idx = list(parent).index(r); parts = []
            if before: parts.append(_mkrun(rPr, before))
            parts.append(_insrun(new_text, u))
            if after: parts.append(_mkrun(rPr, after))
            for j, pt in enumerate(parts): parent.insert(idx + j, pt)
            parent.remove(r); return True
    return False

# (marker, old, new) replacements
EDITS = [
    # #17 — trim SQ1 in the Introduction
    ("identify and translate agentic AI opportunities into value-seeking",
     " into value-seeking initiatives", ""),
    # #13 — sub-question hyphenation consistency (ch5 + conclusion)
    ("The first sub question this paper", "sub question", "sub-question"),
    ("The three subquestions structure this answer", "subquestions", "sub-questions"),
    # #197 — spell out CMO / CTO at first findings use (§4.2.2)
    ("captured the resulting relationship", "the CMO should be",
     "the chief marketing officer (CMO) should be"),
    ("captured the resulting relationship", f"because the CTO{APO}s cooperation",
     f"because the chief technology officer{APO}s (CTO) cooperation"),
    # #234 — remind value = benefits net of costs/risks, cite Woodside (§4.4)
    ("Applying agentic AI creates outcomes for the organization",
     "We analyze these from a value perspective.",
     "We analyze these from a value perspective, understood as the benefits an outcome delivers net of "
     "the sacrifices and risks it carries (Woodside et al., 2008)."),
    # #168 — broken forward ref 4.3.5 -> 4.3.4 (§4.1.2)
    ("make anticipatory investments", "(see section 4.3.5)", "(see section 4.3.4)"),
]
# (marker, anchor, appended) insertions
INSERTS = [
    # #213 — transition sentence at end of §4.2.3 linking to applying
    ("Shadow IT can be a very good lighthouse",
     f"make people understand what is possible.{RDQ}",
     " Having shaped these organizational conditions, the manager can put agentic AI to work; the next "
     "section turns to how it is applied."),
]

def main():
    check = "--check" in sys.argv
    doc = Document(str(DOCX)); u = _used(doc)
    problems = []
    for marker, old, new in EDITS:
        el = find_elem(doc, marker)
        if el is None: problems.append(("NO PARA", marker[:35]))
        elif old not in full_text(el): problems.append(("NO FRAG", f"{marker[:24]} :: {old[:34]}"))
    for marker, anchor, _ in INSERTS:
        el = find_elem(doc, marker)
        if el is None: problems.append(("NO PARA", marker[:35]))
        elif anchor not in full_text(el): problems.append(("NO ANCHOR", f"{marker[:24]} :: {anchor[:34]}"))
    print(f"{len(EDITS)} edits + {len(INSERTS)} inserts")
    for k, w in problems: print(f"  [{k}] {w}")
    if check:
        print("OK to apply." if not problems else "FIX FIRST."); print("--check only."); return
    if problems: print("NOT SAVED."); return
    for marker, old, new in EDITS:
        replace_fragment(find_elem(doc, marker), old, new, u)
    for marker, anchor, txt in INSERTS:
        insert_after(find_elem(doc, marker), anchor, txt, u)
    shutil.copy(DOCX, BACKUP); doc.save(str(DOCX))
    print(f"Applied. Backup: {BACKUP.name}")

if __name__ == "__main__":
    main()
