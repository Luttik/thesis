# -*- coding: utf-8 -*-
"""
Minimal-diff tracked-change fixes (author 'Claude').

'Minimal' = only the changed characters are deleted/inserted. E.g. for
'data suggest' -> 'data suggests' the engine strips the common prefix/suffix
and inserts just 's'.

NOT RUN AUTOMATICALLY — execute deliberately when the docx is free:
    PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/patch_minimal_fixes.py
Control which groups apply via RUN_GROUPS below.
"""
from __future__ import annotations
import copy
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "Thesis Draft - Daan Luttik - MBA - copy from 2026-06-14.docx"
AUTHOR = "Claude"
DATE = "2026-06-14T00:00:00Z"
XS = "{http://www.w3.org/XML/1998/namespace}space"

# which groups to apply when run:
RUN_GROUPS = {"safe", "judgment"}   # add "optional" to include foreword/exec polish


# ---------- tracked-change primitives ----------
def make_rev(doc):
    used = {int(el.get(qn("w:id"), 0)) for el in doc.element.body.iter()
            if el.get(qn("w:id")) is not None}
    c = [max(used, default=0) + 1]
    def nxt():
        v = c[0]; c[0] += 1; return v
    return nxt

def _rpr(src):
    rpr = src.find(qn("w:rPr"));  return copy.deepcopy(rpr) if rpr is not None else None

def _run(src, text, kind):
    r = etree.Element(qn("w:r"))
    rpr = _rpr(src)
    if rpr is not None: r.append(rpr)
    tag = "w:delText" if kind == "del" else "w:t"
    t = etree.SubElement(r, qn(tag)); t.set(XS, "preserve"); t.text = text
    return r

def _wrap(tag, child, rev):
    e = etree.Element(qn(tag))
    e.set(qn("w:id"), str(rev())); e.set(qn("w:author"), AUTHOR); e.set(qn("w:date"), DATE)
    e.append(child); return e

def _cpx(a, b):
    n = 0
    while n < len(a) and n < len(b) and a[n] == b[n]: n += 1
    return n
def _csf(a, b):
    n = 0
    while n < len(a) and n < len(b) and a[-1-n] == b[-1-n]: n += 1
    return n

def visible_text(p):
    out = []
    for t in p.iter(qn("w:t")):
        a = t.getparent(); d = False
        while a is not None:
            if a.tag == qn("w:del"): d = True; break
            a = a.getparent()
        if not d: out.append(t.text or "")
    return "".join(out)


def _edit_range(p, seq, start, end, ins_text, rev):
    """Delete chars [start,end) (tracked) and insert ins_text (tracked) at start."""
    # locate start
    acc = 0; si = sl = None
    for i, (_, _, txt) in enumerate(seq):
        if acc + len(txt) > start or (acc + len(txt) == start and i == len(seq) - 1):
            si = i; sl = start - acc; break
        acc += len(txt)
    if si is None:  # start at very end
        si = len(seq) - 1; sl = len(seq[si][2])
    if start == end:  # pure insertion
        r, t, txt = seq[si]
        t.text = txt[:sl]; after = txt[sl:]
        idx = list(p).index(r)
        p.insert(idx + 1, _run(r, after, "ins"))            # placeholder; replaced below
        # actually: keep 'after' as plain run, insert ins between
        p.remove(p[idx + 1])
        p.insert(idx + 1, _run(r, after, "plain"))
        p.insert(idx + 1, _wrap("w:ins", _run(r, ins_text, "ins"), rev))
        return
    # locate end
    acc = 0; ei = el = None
    for i, (_, _, txt) in enumerate(seq):
        if acc + len(txt) >= end:
            ei = i; el = end - acc; break
        acc += len(txt)
    if si == ei:
        r, t, txt = seq[si]
        before, mid, after = txt[:sl], txt[sl:el], txt[el:]
        t.text = before
        idx = list(p).index(r)
        ins_at = idx + 1
        p.insert(ins_at, _run(r, after, "plain"))
        if ins_text:
            p.insert(ins_at, _wrap("w:ins", _run(r, ins_text, "ins"), rev))
        p.insert(ins_at, _wrap("w:del", _run(r, mid, "del"), rev))
        return
    # multi-run
    rs, ts, txts = seq[si]; re_, te, txte = seq[ei]
    ts.text = txts[:sl]; te.text = txte[el:]
    deln = etree.Element(qn("w:del"))
    deln.set(qn("w:id"), str(rev())); deln.set(qn("w:author"), AUTHOR); deln.set(qn("w:date"), DATE)
    if txts[sl:]: deln.append(_run(rs, txts[sl:], "del"))
    for j in range(si + 1, ei):
        rm, _, txtm = seq[j]
        if txtm: deln.append(_run(rm, txtm, "del"))
        p.remove(rm)
    if txte[:el]: deln.append(_run(re_, txte[:el], "del"))
    idx = list(p).index(rs)
    if ins_text:
        p.insert(idx + 1, _wrap("w:ins", _run(rs, ins_text, "ins"), rev))
    p.insert(idx + 1, deln)


def minimal_replace(p, old, new, rev):
    seq = []
    for r in p.findall(qn("w:r")):
        t = r.find(qn("w:t"))
        if t is not None: seq.append([r, t, t.text or ""])
    S = "".join(x[2] for x in seq)
    pos = S.find(old)
    if pos < 0: return False
    pf = _cpx(old, new)
    sf = _csf(old[pf:], new[pf:])
    start = pos + pf; end = pos + len(old) - sf
    ins_text = new[pf: len(new) - sf]
    _edit_range(p, seq, start, end, ins_text, rev)
    return True


def find_para(doc, anchor, style=None):
    for p in doc.element.body.iter(qn("w:p")):
        if style:
            pPr = p.find(qn("w:pPr")); st = ""
            if pPr is not None:
                ps = pPr.find(qn("w:pStyle"))
                if ps is not None: st = ps.get(qn("w:val")) or ""
            if st != style: continue
        if anchor in visible_text(p):
            return p
    return None


# ---------- edit list: (anchor, old, new, label, group, style?) ----------
OPS = [
    # ---------------- SAFE / mechanical ----------------
    ("a model that combines 4 managerial", "combines 4 managerial", "combines four managerial", "exec: 4->four", "safe", None),
    ("untapped potential that", "potential that  Brinker", "potential that Brinker", "intro double space", "safe", None),
    ("content and campaigns. ", "content and campaigns. ", "content and campaigns ", "4.3.2 heading period", "safe", "Heading3"),
    ("customer-facing agents. ", "customer-facing agents. ", "customer-facing agents ", "4.3.4 heading period", "safe", "Heading3"),
    ("Interviewee 6 describes that they build", "they build  a", "they build a", "4.3.2 double space", "safe", None),
    ("utilizing generic agents for personal work, which", "work, which  refers", "work, which refers", "4.3.3 double space", "safe", None),
    ("only interviewee 7 describes an occurrence of job loss", "job loss ,“What", "job loss, “What", "4.4.2 space-before-comma", "safe", None),
    ("translate agentic AI opportunities", "opportunities?”.", "opportunities?”", "5.1 stray period after ?”", "safe", None),
    ("successful implementation and use of agentic AI.In line", "agentic AI.In line", "agentic AI. In line", "5.1 missing space AI.In", "safe", None),
    # data suggest/show -> singular agreement (minimal: add 's')
    ("the most significant factor is not the agentic AI", "data suggest that, when", "data suggests that, when", "data suggests #1", "safe", None),
    ("this increased speed creates increased resistance", "data suggest that this", "data suggests that this", "data suggests #2", "safe", None),
    ("two key external sources of inspiration", "data show two", "data shows two", "data shows #3", "safe", None),
    # 5.1 risk-patterns paragraph punctuation
    ("a few specific patterns concerning risks", "key risk, however some", "key risk; however some", "5.1 ; before however", "safe", None),
    ("a few specific patterns concerning risks", "however some interviewees", "however, some interviewees", "5.1 , after however", "safe", None),
    ("a few specific patterns concerning risks", "Similarly an often", "Similarly, an often", "5.1 , after Similarly", "safe", None),
    ("a few specific patterns concerning risks", "is brand risk, here we", "is brand risk; here we", "5.1 ; before here", "safe", None),
    ("a few specific patterns concerning risks", "as a risk some note", "as a risk, some note", "5.1 , after risk", "safe", None),
    ("In addition to the points made below", "made below Appendix", "made below, Appendix", "5.2 , after below", "safe", None),
    ("The condition of the marketing team is important", "important, interviewees note", "important; interviewees note", "5.2 ; comma splice", "safe", None),
    ("We advice marketing managers to negotiate", "We advice marketing", "We advise marketing", "5.2 advice->advise", "safe", None),
    ("Acharya, D. B., Kuppan", "goals—A comprehensive", "goals, a comprehensive", "ref Acharya em-dash", "safe", None),
    ("Merriam, S. B. (1998)", 'from" Case', "from Case", "ref Merriam stray quote 1", "safe", None),
    ("Merriam, S. B. (1998)", 'Education.".', "Education.", "ref Merriam stray quote 2", "safe", None),

    # ---------------- JUDGMENT (confirm before running) ----------------
    ("The principal theoretical contribution of this study", "constructed, it shows", "constructed; it shows", "5.1 model-overview comma splice", "judgment", None),
    ("The principal theoretical contribution of this study",
     "which includes, Observing external conditions, including the rapid progression of AI and the accompanying market pressure provide the impetus for change",
     "which includes observing external conditions, including the rapid progression of AI and the accompanying market pressure, which provide the impetus for change",
     "5.1 model-overview list structure", "judgment", None),
    ("if you help them master the skills necessary to work in the new context",
     "in the new context you are as interviewee 13 noted “Yes",
     "in the new context. As interviewee 13 noted: “Yes",
     "5.2 garbled sentence", "judgment", None),

    # ---------------- OPTIONAL (foreword / exec polish) ----------------
    ("Over 10 years ago I fell in love", "the crown to my entire", "the crowning achievement of my entire", "foreword: crown to", "optional", None),
    ("I want to thank the people who have brought me here", "Also I want to thank", "I also want to thank", "foreword: Also I", "optional", None),
    ("a very special thanks", "special thanks for my peer", "special thanks to my peer", "foreword: thanks to", "optional", None),
    ("one of the earliest empirical works on agentic AI", "And in doing so", "In doing so", "exec: drop leading And", "optional", None),
    ("one of the earliest empirical works on agentic AI", "earliest empirical works on agentic", "earliest empirical studies on agentic", "exec: works->studies", "optional", None),
]


def main():
    doc = Document(str(DOCX))
    rev = make_rev(doc)
    applied = skipped = 0
    for anchor, old, new, label, group, style in OPS:
        if group not in RUN_GROUPS:
            continue
        p = find_para(doc, anchor, style)
        if p is None or not minimal_replace(p, old, new, rev):
            print(f"  [MISS] ({group}) {label}: {old!r}")
            skipped += 1
        else:
            print(f"  [OK]   ({group}) {label}")
            applied += 1
    doc.save(str(DOCX))
    print(f"\nApplied {applied}, missed {skipped}. Groups run: {sorted(RUN_GROUPS)}")


if __name__ == "__main__":
    main()
