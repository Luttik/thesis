# -*- coding: utf-8 -*-
"""Ground the optics-vs-reality gap (tracked, author 'Claude').

Chapter 4 dropped the optics/reality finding (old 4.5.3) but chapter 5 still
discusses it. Re-add a brief finding to 4.1.1 (AI progression), framed as
separating real capability from hype, using the recovered interviewee quotes,
and re-attach (see Section 4.1.1) pointers in the two chapter-5 spots."""
from __future__ import annotations
import copy, shutil, sys
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

DOCX = Path(__file__).resolve().parents[1] / "Thesis Draft - Daan Luttik - MBA - copy from 2026-06-13.docx"
BACKUP = DOCX.with_suffix(".optics-backup.docx")
AUTHOR = "Claude"; DATE = "2026-06-13T16:45:00Z"
XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"
LDQ, RDQ, APO = "“", "”", "’"

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

def ins_paragraph(text, u):
    """A whole new paragraph, content + paragraph-mark both tracked-inserted."""
    p = etree.Element(qn("w:p")); pPr = etree.SubElement(p, qn("w:pPr"))
    rPr = etree.SubElement(pPr, qn("w:rPr"))
    im = etree.SubElement(rPr, qn("w:ins")); im.set(qn("w:id"), str(_nid(u)))
    im.set(qn("w:author"), AUTHOR); im.set(qn("w:date"), DATE)
    p.append(_insrun(text, u))
    return p

def insert_text_after(p_elem, anchor, new_text, u):
    """Insert new_text (tracked) immediately after `anchor` within the paragraph."""
    runs = p_elem.findall(qn("w:r")); segs = []; total = ""
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
            rPr = r.find(qn("w:rPr")); parent = r.getparent(); idx = list(parent).index(r)
            parts = []
            if before: parts.append(_mkrun(rPr, before))
            parts.append(_insrun(new_text, u))
            if after: parts.append(_mkrun(rPr, after))
            for j, pt in enumerate(parts): parent.insert(idx + j, pt)
            parent.remove(r); return True
    return False

OPTICS = (
    f"Observing AI progression also means separating real capability from its optics, as agentic "
    f"capability is frequently presented before it is operationally present. Interviewee 9 acknowledged "
    f"this directly: {LDQ}I think we sometimes present something a certain way while we{APO}re trying to "
    f"actually make it that way in the background.{RDQ} Interviewee 12 described the same pattern, noting "
    f"that organizations {LDQ}say that you have something that you don{APO}t really have, and then you go "
    f"and build it really quickly.{RDQ} None of the interviewees doubted the underlying value of agentic "
    f"AI; the concern is inflated expectation. As interviewee 11 cautioned, {LDQ}The big thing is hype. So "
    f"AI is being overpromised all the time. And we have to reduce expectations.{RDQ}"
)

def main():
    check = "--check" in sys.argv
    doc = Document(str(DOCX)); u = _used(doc)
    anchor = find_elem(doc, "rate of productization of AI")
    c5a = find_elem(doc, "optics can be especially deceiving")
    c5b = find_elem(doc, "Another limitation lies in the gap between optics and reality")
    probs = []
    if anchor is None: probs.append("4.1.1 productization anchor NOT FOUND")
    if c5a is None: probs.append("ch5 §5.1.2 optics paragraph NOT FOUND")
    elif "the reality of these AI solutions" not in full_text(c5a): probs.append("§5.1.2 insert point NOT FOUND")
    if c5b is None: probs.append("ch5 §5.3 optics limitation NOT FOUND")
    elif "gap between optics and reality" not in full_text(c5b): probs.append("§5.3 insert point NOT FOUND")
    print(f"anchors: 4.1.1={'ok' if anchor is not None else 'MISS'}  §5.1.2={'ok' if c5a is not None else 'MISS'}  §5.3={'ok' if c5b is not None else 'MISS'}")
    if probs:
        for p in probs: print("  PROBLEM:", p)
    if check:
        print("--check only."); return
    if probs:
        print("NOT SAVED."); return
    # 1. insert finding paragraph after productization para
    para = ins_paragraph(OPTICS, u)
    parent = anchor.getparent(); parent.insert(list(parent).index(anchor) + 1, para)
    # 2. re-attach pointers in ch5
    insert_text_after(c5a, "the reality of these AI solutions", " (see Section 4.1.1)", u)
    insert_text_after(c5b, "gap between optics and reality", " (see Section 4.1.1)", u)
    shutil.copy(DOCX, BACKUP); doc.save(str(DOCX))
    print(f"Applied. Backup: {BACKUP.name}")

if __name__ == "__main__":
    main()
