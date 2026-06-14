# -*- coding: utf-8 -*-
"""
Apply grammar / citation fixes as tracked changes (author 'Claude').

Robust multi-run replacement: each target string may span several fragmented
<w:r> runs (direct children of the paragraph). We locate the paragraph by a
visible-text anchor, then replace `old` -> `new` as a tracked deletion + insertion
so the edit is accept/reject safe.

Run with:
    PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/patch_grammar_fixes.py
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

XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"


def make_rev(doc):
    used = {int(el.get(qn("w:id"), 0)) for el in doc.element.body.iter()
            if el.get(qn("w:id")) is not None}
    c = [max(used, default=0) + 1]
    def nxt():
        v = c[0]; c[0] += 1; return v
    return nxt


def visible_text(p):
    out = []
    for t in p.iter(qn("w:t")):
        anc = t.getparent(); indel = False
        while anc is not None:
            if anc.tag == qn("w:del"):
                indel = True; break
            anc = anc.getparent()
        if not indel:
            out.append(t.text or "")
    return "".join(out)


def _rpr(src):
    rpr = src.find(qn("w:rPr"))
    return copy.deepcopy(rpr) if rpr is not None else None


def _plain_run(src, text):
    r = etree.Element(qn("w:r"))
    rpr = _rpr(src)
    if rpr is not None:
        r.append(rpr)
    t = etree.SubElement(r, qn("w:t"))
    t.set(XMLSPACE, "preserve")
    t.text = text
    return r


def _del_run(src, text):
    r = etree.Element(qn("w:r"))
    rpr = _rpr(src)
    if rpr is not None:
        r.append(rpr)
    dt = etree.SubElement(r, qn("w:delText"))
    dt.set(XMLSPACE, "preserve")
    dt.text = text
    return r


def _wrap_del(run, rid):
    d = etree.Element(qn("w:del"))
    d.set(qn("w:id"), str(rid)); d.set(qn("w:author"), AUTHOR); d.set(qn("w:date"), DATE)
    d.append(run)
    return d


def _ins(src, text, rid):
    ins = etree.Element(qn("w:ins"))
    ins.set(qn("w:id"), str(rid)); ins.set(qn("w:author"), AUTHOR); ins.set(qn("w:date"), DATE)
    ins.append(_plain_run(src, text))
    return ins


def replace_first(p, old, new, rev):
    """Replace first occurrence of `old` (may span runs) within paragraph p. Tracked."""
    seq = []  # (run, t_elem, text) for direct-child runs bearing w:t
    for r in p.findall(qn("w:r")):
        t = r.find(qn("w:t"))
        if t is not None:
            seq.append([r, t, t.text or ""])
    S = "".join(x[2] for x in seq)
    pos = S.find(old)
    if pos < 0:
        return False
    end = pos + len(old)

    # locate start run/local offset
    acc = 0; si = sl = None
    for i, (_, _, txt) in enumerate(seq):
        if acc + len(txt) > pos:
            si = i; sl = pos - acc; break
        acc += len(txt)
    # locate end run/local offset (run containing char end-1)
    acc = 0; ei = el = None
    for i, (_, _, txt) in enumerate(seq):
        if acc + len(txt) >= end:
            ei = i; el = end - acc; break
        acc += len(txt)

    parent = p
    rid = rev()

    if si == ei:
        r, t, txt = seq[si]
        before, after = txt[:sl], txt[el:]
        t.text = before
        idx = list(parent).index(r)
        # insert in order: del, ins, after  -> [r(before), del, ins, after]
        parent.insert(idx + 1, _plain_run(r, after))
        parent.insert(idx + 1, _ins(r, new, rid))
        parent.insert(idx + 1, _wrap_del(_del_run(r, old), rid))
        return True

    # multi-run
    rs, ts, txts = seq[si]
    re_, te, txte = seq[ei]
    before = txts[:sl]
    del_first = txts[sl:]
    del_last = txte[:el]
    after = txte[el:]
    ts.text = before
    te.text = after

    del_el = etree.Element(qn("w:del"))
    del_el.set(qn("w:id"), str(rid)); del_el.set(qn("w:author"), AUTHOR); del_el.set(qn("w:date"), DATE)
    if del_first:
        del_el.append(_del_run(rs, del_first))
    for j in range(si + 1, ei):
        rm, _, txtm = seq[j]
        if txtm:
            del_el.append(_del_run(rm, txtm))
        parent.remove(rm)
    if del_last:
        del_el.append(_del_run(re_, del_last))

    idx = list(parent).index(rs)
    parent.insert(idx + 1, _ins(rs, new, rid))
    parent.insert(idx + 1, del_el)
    return True


def find_para(doc, anchor):
    for p in doc.element.body.iter(qn("w:p")):
        if anchor in visible_text(p):
            return p
    return None


def do(doc, anchor, old, new, rev, all_occ=False, label=""):
    p = find_para(doc, anchor)
    if p is None:
        print(f"  [MISS-PARA] {label or old!r}: anchor not found: {anchor!r}")
        return 0
    n = 0
    if all_occ:
        while replace_first(p, old, new, rev):
            n += 1
            p = find_para(doc, anchor)  # refind (tree changed); anchor stable
            if p is None:
                break
    else:
        if replace_first(p, old, new, rev):
            n = 1
    if n == 0:
        print(f"  [MISS-TEXT] {label or old!r}: old not found in paragraph")
    else:
        print(f"  [OK x{n}] {label or old[:40]!r}")
    return n


# (anchor, old, new, all_occ, label)
OPS = [
    # --- Intro ---
    ("one-third of the estimated", "$4.4 trillion in estimated annual", "$4.4 trillion in annual", False, "intro double-estimated"),
    ("unlock the large productivity", "the large productivity mentioned by Mayer et al (2025)", "the large productivity gains mentioned by Mayer et al. (2025)", False, "intro productivity+Mayer et al."),
    # --- 2.1.2 ---
    ("Vaid et al (2025) note that GenAI", "Vaid et al (2025)", "Vaid et al. (2025)", True, "Vaid et al. period x2"),
    # --- 2.2 ---
    ("Moralles et al. (2026) notes that literature", "Moralles et al. (2026) notes that literature", "Moralles et al. (2026) note that literature", False, "Moralles note"),
    ("Moralles et al. (2026) defines it", "Moralles et al. (2026) defines it", "Moralles et al. (2026) define it", False, "Moralles define"),
    ("and Srivastav (2026) called", "Srivastav (2026)", "Srivastava (2026)", False, "Srivastava typo"),
    ("data is not readily available). However, this research",
     "data is not readily available). However, this research",
     "data is not readily available), it becomes difficult to delegate that process to an agent. However, this research", False, "Schmidt incomplete sentence"),
    # --- 2.3 ---
    ("“self-actualization” (Woodside et al., 2008)", "“self-actualization” (Woodside et al., 2008)", "“self-actualization” (Almquist et al., 2016)", False, "Almquist not Woodside"),
    # --- 2.4 ---
    ("Enholm et al (2022) and Holmström", "Enholm et al (2022)", "Enholm et al. (2022)", True, "Enholm et al. period x3"),
    ("describe a concerning pattern which he calls", "which he calls the digitalization paradox", "which they call the digitalization paradox", False, "Gebauer he->they"),
    ("Gebauer et al. (2020) notes key traps", "Gebauer et al. (2020) notes key traps", "Gebauer et al. (2020) note key traps", False, "Gebauer notes->note"),
    # --- 4.1.1 ---
    ("describe the progression of AI with enthusiasm", "with enthusiasm. Interviewee 4 noted", "with enthusiasm, interviewee 4 noted", False, "enthusiasm fragment"),
    # --- 4.2.2 ---
    ("you have no one taking care of that", "no one taking care of that,” Interviewee 5", "no one taking care of that.” Interviewee 5", False, "taking care comma-splice"),
    # --- 4.3.1 ---
    ("dump it in, and then have it analyzed", "have it analyzed,” this was required", "have it analyzed.” This was required", False, "analyzed comma-splice"),
    ("if I try to dump anything over 30", "doesn’t do it,”.", "doesn’t do it.”", False, "doesn't do it punctuation"),
    # --- 4.3.4 ---
    ("employing customer-facing agents with refers", "customer-facing agents with refers to letting", "customer-facing agents, which refers to letting", False, "4.3.4 with->which"),
    # --- 4.4.1 ---
    ("cluster around four themes", "four themes: Efficiency, scalability", "four themes: efficiency, scalability", False, "four themes lowercase"),
    ("When asked about the benefits of agentic AI, interviewee three", "interviewee three notes", "interviewee 3 notes", False, "interviewee three->3"),
    ("Scalability refers to the ability", "the ability of doing more units of work with the same amount of work;", "the ability to do more units of work with the same amount of effort;", False, "scale ability-to-do"),
    ("Scalability refers to the ability", "in bulk. is the benefit most clearly impossible", "in bulk. Scale is the benefit most clearly impossible", False, "scale missing subject"),
    ("Participants repeatedly described AI enabling work", "could not previously do: Typically relating", "could not previously do, typically relating", False, "do: Typically"),
    ("Improvements in quality of output come in", "come in various different forms and notes how the agentic system produces", "come in various forms; the agentic system produces", False, "various different / notes how"),
    # --- 5.1 ---
    ("Four key use cases that marketing managers can apply are observed", "utilizing generic agents for personal work and employing cusomter-facing agents", "utilizing generic agents for personal work, and employing customer-facing agents", False, "cusomter + oxford comma"),
    ("Four key use cases that marketing managers can apply are observed", "are observed; generating insights", "are observed: generating insights", False, "observed colon"),
    ("Interviewees note the breath of analytical", "the breath of analytical use cases, they span use-cases", "the breadth of analytical use cases; they span use cases", False, "breadth / comma splice"),
    ("they use tools that do not required", "do not required programming experience", "do not require programming experience", False, "do not require"),
    ("a sales representative, and a agent that can be used", "and a agent that can be used", "and an agent that can be used", False, "a agent->an agent"),
    ("integrated with the consumers agentic AI system", "the consumers agentic AI system", "the consumer’s agentic AI system", False, "consumer's"),
    ("while still in an experimental phase companies start", "in an experimental phase companies start", "in an experimental phase, companies start", False, "experimental phase comma"),
    ("The models final components concerns the value outcome", "The models final components concerns the value outcome", "The model’s final component concerns the value outcome", False, "model's final component"),
    ("specific benefits, sacrifices, and risks that described in this study", "risks that described in this study", "risks that are described in this study", False, "that are described"),
    ("scale, and quality of output are present in", "are present in are described by Hughes", "are described by Hughes", False, "are present in are described"),
    ("This study confirms these effects of agentic AI empirically", "empirically and show that they apply", "empirically and shows that they apply", False, "show->shows"),
    ("Interviewees seem to marketers see this pattern", "Interviewees seem to marketers see this pattern", "Interviewees see this pattern", False, "seem to marketers see"),
    ("by analyzing how the are mediated", "analyzing how the are mediated by", "analyzing how they are mediated by", False, "how they are mediated"),
    ("The organizational context stands and managerial behaviors in general stand out", "The organizational context stands and managerial behaviors in general stand out", "The organizational context and managerial behaviors in general stand out", False, "context stands leftover"),
    ("some note that they use AI to ensure validate quality", "use AI to ensure validate quality", "use AI to validate quality", False, "ensure validate"),
    # --- 5.2 ---
    ("create value using agentic AI and key element in doing so", "agentic AI and key element in doing so is navigating", "agentic AI, and a key element in doing so is navigating", False, "key element"),
    ("directly applicable for a marketer manager", "applicable for a marketer manager", "applicable for a marketing manager", False, "marketer->marketing"),
    ("Vidal et al. (2022) notes that digital leaders", "Vidal et al. (2022) notes that digital leaders", "Vidal et al. (2022) note that digital leaders", False, "Vidal notes->note (5.2)"),
    # --- 5.3 ---
    ("the speed with which AI is evolving rapidly", "the speed with which AI is evolving rapidly", "the speed at which AI is evolving", False, "evolving rapidly redundant"),
    # --- References ---
    ("Constructing grounded theory (introducing", "). Constr. grounded theory.", "). Sage.", False, "Charmaz publisher"),
]


def delete_vaid_doi(doc, rev):
    """Tracked-delete the stray duplicated SMJ882 hyperlinks before the Vaid entry."""
    target = None
    for p in doc.element.body.iter(qn("w:p")):
        if "Vaid, S., Puntoni" in visible_text(p) and "AID-SMJ882" in "".join(t.text or "" for t in p.iter(qn("w:t"))):
            target = p; break
    if target is None:
        print("  [MISS] Vaid DOI paragraph not found")
        return 0
    n = 0
    for hl in target.findall(qn("w:hyperlink")):
        htext = "".join(t.text or "" for t in hl.iter(qn("w:t")))
        if "AID-SMJ882" not in htext:
            continue
        # convert each run's w:t -> w:delText and wrap run in <w:del>
        for r in hl.findall(qn("w:r")):
            t = r.find(qn("w:t"))
            if t is None:
                continue
            txt = t.text or ""
            r.remove(t)
            dt = etree.SubElement(r, qn("w:delText"))
            dt.set(XMLSPACE, "preserve"); dt.text = txt
            rid = rev()
            d = etree.Element(qn("w:del"))
            d.set(qn("w:id"), str(rid)); d.set(qn("w:author"), AUTHOR); d.set(qn("w:date"), DATE)
            idx = list(hl).index(r)
            hl.insert(idx, d)
            hl.remove(r)
            d.append(r)
            n += 1
    print(f"  [OK] Vaid DOI: wrapped {n} stray hyperlink run(s) as tracked deletion")
    return n


def main():
    print(f"Opening {DOCX.name}")
    doc = Document(str(DOCX))
    rev = make_rev(doc)
    applied = 0
    for anchor, old, new, all_occ, label in OPS:
        applied += do(doc, anchor, old, new, rev, all_occ, label)
    applied += delete_vaid_doi(doc, rev)
    doc.save(str(DOCX))
    print(f"\nSaved. Total tracked edits: {applied}")


if __name__ == "__main__":
    main()
