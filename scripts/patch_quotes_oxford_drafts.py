# -*- coding: utf-8 -*-
"""Typographic + Oxford-comma cleanup, plus the two reviewed drafts (#135, #247),
all tracked (author 'Claude').
- Convert 12 stray straight quotes/apostrophes to curly.
- Add the serial (Oxford) comma to 4 genuine three-item lists.
- Insert the Figure-1 description (#135, replacing the old §4 roadmap paragraph)
  and the divergent-outcomes bridging paragraph (#247)."""
from __future__ import annotations
import copy, shutil, sys
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

DOCX = Path(__file__).resolve().parents[1] / "Thesis Draft - Daan Luttik - MBA - copy from 2026-06-13.docx"
BACKUP = DOCX.with_suffix(".quotes-backup.docx")
AUTHOR = "Claude"; DATE = "2026-06-13T18:20:00Z"
XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"

def _used(doc): return {int(el.get(qn("w:id"), 0)) for el in doc.element.body.iter() if el.get(qn("w:id")) is not None}
def _nid(u): n = max(u, default=0) + 1; u.add(n); return n
def _stamp(el, u): el.set(qn("w:id"), str(_nid(u))); el.set(qn("w:author"), AUTHOR); el.set(qn("w:date"), DATE)
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
    ins = etree.Element(qn("w:ins")); _stamp(ins, u)
    r = etree.SubElement(ins, qn("w:r")); t = etree.SubElement(r, qn("w:t"))
    t.set(XMLSPACE, "preserve"); t.text = s
    return ins
def _wrap_run_in_del(r, u):
    d = etree.Element(qn("w:del")); _stamp(d, u)
    rc = copy.deepcopy(r)
    for t in rc.findall(qn("w:t")):
        dt = etree.Element(qn("w:delText")); dt.set(XMLSPACE, "preserve"); dt.text = t.text or ""
        t.getparent().replace(t, dt)
    d.append(rc); return d

def replace_fragment(p, old, new, u):
    runs = p.findall(qn("w:r")); segs = []; total = ""
    for r in runs:
        t = r.find(qn("w:t")); txt = t.text if (t is not None and t.text) else ""
        segs.append((r, txt)); total += txt
    start = total.find(old)
    if start < 0: return False
    end = start + len(old); pos = 0; inserted = False
    def mk_del(rPr, s):
        d = etree.Element(qn("w:del")); _stamp(d, u)
        dr = etree.SubElement(d, qn("w:r"))
        if rPr is not None: dr.insert(0, copy.deepcopy(rPr))
        dt = etree.SubElement(dr, qn("w:delText")); dt.set(XMLSPACE, "preserve"); dt.text = s
        return d
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

def ins_paragraph(text, u):
    p = etree.Element(qn("w:p")); pPr = etree.SubElement(p, qn("w:pPr"))
    rPr = etree.SubElement(pPr, qn("w:rPr")); _stamp(etree.SubElement(rPr, qn("w:ins")), u)
    p.append(_insrun(text, u)); return p

def del_para_deep(p, u):
    pPr = p.find(qn("w:pPr"))
    if pPr is None: pPr = etree.Element(qn("w:pPr")); p.insert(0, pPr)
    rPr = pPr.find(qn("w:rPr"))
    if rPr is None: rPr = etree.SubElement(pPr, qn("w:rPr"))
    if rPr.find(qn("w:del")) is None:
        dm = etree.Element(qn("w:del")); _stamp(dm, u); rPr.insert(0, dm)
    for r in p.findall(qn("w:r")): p.replace(r, _wrap_run_in_del(r, u))
    for ins in p.findall(qn("w:ins")):
        for r in ins.findall(qn("w:r")): ins.replace(r, _wrap_run_in_del(r, u))

DQ = chr(34)
QUOTES = [
    ("exploratory nature reflects", "question's", "question’s"),
    ("academic background in AI", "researcher's", "researcher’s"),
    ("You have to act", "can't", "can’t"),
    ("rather have something live", "I'd", "I’d"),
    ("the laboratory, where you", "you're", "you’re"),
    ("Provide freedom to experiment", "don't", "don’t"),
    ("early learnings", "don't", "don’t"),
    ("many marketing teams it", "it's", "it’s"),
    ("decide what to automate", "automate?" + DQ, "automate?”"),
    ("Yet users", "users'", "users’"),
    ("spend more with us", "we'll", "we’ll"),
    ("support for her customers", "customers'", "customers’"),
]
OXFORD = [
    ("integrate data, make decisions", "make decisions and execute campaigns",
     "make decisions, and execute campaigns"),
    ("their background, role", "role and type of company", "role, and type of company"),
    ("the right capabilities", "implement or integrate", "implement, or integrate"),
    ("for content creation", "deployment and evaluation", "deployment, and evaluation"),
]
TEXT_247 = ("Taken together, the benefits, sacrifices, and risks above describe the value agentic AI can "
            "produce. Their realization, however, is highly uneven: the same use case proved transformative "
            "in one organization and stalled in another. Table 5 illustrates this divergence for the three "
            "most frequently reported use cases.")
TEXT_135 = ("Figure 1 presents the resulting process model. It shows how the studied marketing managers "
            "observed an impulse for change in their external environment, navigated the organizational "
            "conditions that enable or constrain a response, applied agentic AI through specific use cases, "
            "and obtained value outcomes. Running through this chain is a set of paradoxes, in which the "
            "technology that creates a problem also supplies the means to manage it. We discuss these "
            "elements in turn below: first the external conditions managers observed, then how they "
            "navigated the organizational context, the use cases through which they applied agentic AI, and "
            "finally the value outcomes (benefits, sacrifices, and risks) that resulted.")

def main():
    check = "--check" in sys.argv
    doc = Document(str(DOCX)); u = _used(doc)
    probs = []
    for marker, old, new in QUOTES + OXFORD:
        el = find_elem(doc, marker)
        if el is None: probs.append(("NO PARA", marker[:30]))
        elif old not in full_text(el): probs.append(("NO FRAG", f"{marker[:18]}::{old[:24]}"))
    anchor247 = find_elem(doc, "strongest incentive to invest in AI-driven brand control")
    anchor135 = find_elem(doc, "Below, we first describe the impulse")
    if anchor247 is None: probs.append(("NO ANCHOR", "#247 brand-control"))
    if anchor135 is None: probs.append(("NO ANCHOR", "#135 below-we-first"))
    print(f"{len(QUOTES)} quotes + {len(OXFORD)} oxford + 2 drafts")
    for k, w in probs: print(f"  [{k}] {w}")
    if check:
        print("OK." if not probs else "FIX FIRST."); return
    if probs:
        print("NOT SAVED."); return
    for marker, old, new in QUOTES + OXFORD:
        if not replace_fragment(find_elem(doc, marker), old, new, u):
            print("WARN unmatched:", marker[:20], old[:20])
    # #247: bridging paragraph before the table
    p = ins_paragraph(TEXT_247, u)
    anchor247.addnext(p)
    # #135: new figure paragraph before old roadmap, then deep-delete old
    newp = ins_paragraph(TEXT_135, u)
    anchor135.addprevious(newp)
    del_para_deep(anchor135, u)
    shutil.copy(DOCX, BACKUP); doc.save(str(DOCX))
    print(f"Applied. Backup: {BACKUP.name}")

if __name__ == "__main__":
    main()
