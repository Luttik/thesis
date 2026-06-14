# -*- coding: utf-8 -*-
"""Tracked-delete orphan reference entries + fix one 'et al.' comma.
Run: PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/patch_ref_orphans.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from docx import Document
from docx.oxml.ns import qn
from lxml import etree
from patch_grammar_fixes import make_rev, find_para, replace_first, visible_text, AUTHOR, DATE, DOCX


def del_paragraph(p, rev):
    """Tracked-delete an entire paragraph: wrap every run's text as <w:del>/<w:delText>
    and mark the paragraph mark as deleted so it merges away on accept."""
    n = 0
    for r in list(p.iter(qn("w:r"))):
        t = r.find(qn("w:t"))
        if t is None:
            continue
        # skip if already inside a del
        anc = r.getparent(); indel = False
        while anc is not None:
            if anc.tag == qn("w:del"): indel = True; break
            anc = anc.getparent()
        if indel:
            continue
        txt = t.text or ""
        r.remove(t)
        dt = etree.SubElement(r, qn("w:delText"))
        dt.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        dt.text = txt
        parent = r.getparent()
        idx = list(parent).index(r)
        d = etree.Element(qn("w:del"))
        rid = rev()
        d.set(qn("w:id"), str(rid)); d.set(qn("w:author"), AUTHOR); d.set(qn("w:date"), DATE)
        parent.insert(idx, d)
        parent.remove(r)
        d.append(r)
        n += 1
    # mark paragraph-mark deletion
    pPr = p.find(qn("w:pPr"))
    if pPr is None:
        pPr = etree.Element(qn("w:pPr"))
        p.insert(0, pPr)
    rPr = pPr.find(qn("w:rPr"))
    if rPr is None:
        rPr = etree.SubElement(pPr, qn("w:rPr"))
    if rPr.find(qn("w:del")) is None:
        d = etree.SubElement(rPr, qn("w:del"))
        rid = rev()
        d.set(qn("w:id"), str(rid)); d.set(qn("w:author"), AUTHOR); d.set(qn("w:date"), DATE)
    return n


ORPHANS = [
    "Chintalapati, S., & Pandey",
    "Kaartemo, V., & Helkkula",
    "Kitsios, F., & Kamariotou",
    "Kumar, V., Kotler, P., Gupta, S., & Rajan",
    "Li, C., Ashraf, S. F., Amin, S., & Safdar",
    "Orlikowski, W. J. (2000)",
    "Prasad Agrawal, K. (2023)",
    "SAS. (2025). Marketers and AI",
    "Sidorchuk, R. (2015)",
]


def main():
    doc = Document(str(DOCX))
    rev = make_rev(doc)

    # locate reference section bounds (so we only delete inside it)
    body = doc.element.body
    paras = list(body.iter(qn("w:p")))
    def style(p):
        pPr = p.find(qn("w:pPr"));
        if pPr is not None:
            ps = pPr.find(qn("w:pStyle"))
            if ps is not None: return ps.get(qn("w:val")) or ""
        return ""
    ref_start = ref_end = None
    for i, p in enumerate(paras):
        tx = visible_text(p)
        if ref_start is None and style(p) == "Heading1" and "References" in tx:
            ref_start = i
        elif ref_start is not None and style(p) == "Heading1" and "Appendix" in tx:
            ref_end = i; break
    ref_set = set(paras[ref_start+1:ref_end])

    print("Deleting orphan references (tracked):")
    for anchor in ORPHANS:
        hit = None
        for p in paras:
            if p in ref_set and anchor in visible_text(p):
                hit = p; break
        if hit is None:
            print(f"  [MISS] {anchor!r}")
            continue
        runs = del_paragraph(hit, rev)
        print(f"  [OK] {anchor[:45]!r}  ({runs} run(s))")

    # et al. comma fix in 5.3
    p = find_para(doc, "transformations (e.g. Vidal et al. 2022)")
    if p is not None and replace_first(p, "(e.g. Vidal et al. 2022)", "(e.g., Vidal et al., 2022)", rev):
        print("  [OK] et al. comma: (e.g., Vidal et al., 2022)")
    else:
        print("  [MISS] et al. comma fix")

    doc.save(str(DOCX))
    print("Saved.")


if __name__ == "__main__":
    main()
