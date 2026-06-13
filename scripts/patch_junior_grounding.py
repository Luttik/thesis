# -*- coding: utf-8 -*-
"""Ground the junior-pipeline threat in 4.4.1 (tracked, author 'Claude').

Ch5 (§5.1.5, §5.2.6) and the Conclusion assert that deploying AI on junior tasks
erodes the junior->senior pipeline and cite 4.4.1, but 4.4.1 only carries the
junior *benefit*. Append a brief threat note (interviewee 10) to that paragraph."""
from __future__ import annotations
import copy, shutil, sys
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

DOCX = Path(__file__).resolve().parents[1] / "Thesis Draft - Daan Luttik - MBA - copy from 2026-06-13.docx"
BACKUP = DOCX.with_suffix(".junior-backup.docx")
AUTHOR = "Claude"; DATE = "2026-06-13T17:10:00Z"
XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"
LDQ, RDQ, ELL = "“", "”", "…"

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

def insert_text_after(p_elem, anchor, new_text, u):
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

ANCHOR = f"I need one, a junior, and he can do the same thing.{RDQ}"
ADDITION = (
    f" Yet this efficiency carries a longer-term risk, because deploying agentic AI first on junior tasks "
    f"can erode the pipeline through which juniors become seniors. Interviewee 10 cautioned that when AI "
    f"absorbs the easiest, typically junior, tasks, {LDQ}you no longer develop juniors into seniors {ELL} "
    f"a major risk: no new talent pipeline.{RDQ}"
)

def main():
    check = "--check" in sys.argv
    doc = Document(str(DOCX)); u = _used(doc)
    p = find_elem(doc, "reshapes the seniority mix of work")
    ok = p is not None and ANCHOR in full_text(p)
    print(f"4.4.1 junior paragraph: {'found' if p is not None else 'MISSING'}; anchor: {'ok' if ok else 'MISSING'}")
    if check:
        print("--check only."); return
    if not ok:
        print("NOT SAVED."); return
    insert_text_after(p, ANCHOR, ADDITION, u)
    shutil.copy(DOCX, BACKUP); doc.save(str(DOCX))
    print(f"Applied. Backup: {BACKUP.name}")

if __name__ == "__main__":
    main()
