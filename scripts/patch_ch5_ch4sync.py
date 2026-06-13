# -*- coding: utf-8 -*-
"""Sync chapter 5 cross-references to the current chapter 4 structure (tracked,
author 'Claude').

Chapter 4 was restructured: 4.1.3 (Supplier communication), 4.4.4 (Driving Value
Outcomes) and the whole 4.5 Paradoxes section were dissolved; 4.2 was reordered
(old 4.2.1 Org capacity + 4.2.2 Leadership -> new 4.2.1 Steering the marketing
department; old 4.2.3 Technical resources -> new 4.2.2; old 4.2.4 Governance ->
new 4.2.3). This repoints chapter 5's references accordingly, keeps the
Discussion prose, drops dangling pointers to deleted findings, and renumbers the
bare 5.1.x sub-headings. All-or-nothing save with backup.

Usage:
    python patch_ch5_ch4sync.py --check   # validate fragments, no write
    python patch_ch5_ch4sync.py           # apply + save (needs Word closed)
"""
from __future__ import annotations
import copy, shutil, sys
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
DOCX_PATH = ROOT / "Thesis Draft - Daan Luttik - MBA - copy from 2026-06-13.docx"
BACKUP = ROOT / "Thesis Draft - Daan Luttik - MBA - copy from 2026-06-13.ch5sync-backup.docx"
AUTHOR = "Claude"
DATE = "2026-06-13T15:30:00Z"
XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"


def _used_ids(doc):
    return {int(el.get(qn("w:id"), 0)) for el in doc.element.body.iter()
            if el.get(qn("w:id")) is not None}


def _nid(used):
    n = max(used, default=0) + 1
    used.add(n)
    return n


def full_text(p):
    return "".join(t.text or "" for t in p.iter(qn("w:t")))


def find_elem(doc, marker):
    for p in doc.paragraphs:
        if marker in full_text(p._element):
            return p._element
    return None


def _ins_run(text, used):
    ins = etree.Element(qn("w:ins")); ins.set(qn("w:id"), str(_nid(used)))
    ins.set(qn("w:author"), AUTHOR); ins.set(qn("w:date"), DATE)
    r = etree.SubElement(ins, qn("w:r")); t = etree.SubElement(r, qn("w:t"))
    t.set(XMLSPACE, "preserve"); t.text = text
    return ins


def replace_fragment_tracked(p_elem, old, new, used):
    runs = p_elem.findall(qn("w:r"))
    segs, total = [], ""
    for r in runs:
        t = r.find(qn("w:t")); txt = t.text if (t is not None and t.text) else ""
        segs.append((r, txt)); total += txt
    start = total.find(old)
    if start < 0:
        return False
    end = start + len(old)

    def mk_run(rPr, s):
        nr = etree.Element(qn("w:r"))
        if rPr is not None: nr.append(copy.deepcopy(rPr))
        tt = etree.SubElement(nr, qn("w:t")); tt.set(XMLSPACE, "preserve"); tt.text = s
        return nr

    def mk_del(rPr, s):
        d = etree.Element(qn("w:del")); d.set(qn("w:id"), str(_nid(used)))
        d.set(qn("w:author"), AUTHOR); d.set(qn("w:date"), DATE)
        dr = etree.SubElement(d, qn("w:r"))
        if rPr is not None: dr.insert(0, copy.deepcopy(rPr))
        dt = etree.SubElement(dr, qn("w:delText")); dt.set(XMLSPACE, "preserve"); dt.text = s
        return d

    pos, inserted = 0, False
    for r, txt in segs:
        r_start, r_end = pos, pos + len(txt); pos = r_end
        if not txt or r_end <= start or r_start >= end:
            continue
        rPr = r.find(qn("w:rPr"))
        ls = max(start, r_start) - r_start; le = min(end, r_end) - r_start
        before, deleted, after = txt[:ls], txt[ls:le], txt[le:]
        parent = r.getparent(); idx = list(parent).index(r)
        parts = []
        if before: parts.append(mk_run(rPr, before))
        if not inserted and new:
            parts.append(_ins_run(new, used)); inserted = True
        elif not inserted:
            inserted = True  # pure deletion, nothing to insert
        if deleted: parts.append(mk_del(rPr, deleted))
        if after: parts.append(mk_run(rPr, after))
        for j, part in enumerate(parts): parent.insert(idx + j, part)
        parent.remove(r)
    return True


def insert_heading_number(p_elem, number, used):
    """Prepend a tracked '<number><tab>' to a bare sub-heading."""
    ins = etree.Element(qn("w:ins")); ins.set(qn("w:id"), str(_nid(used)))
    ins.set(qn("w:author"), AUTHOR); ins.set(qn("w:date"), DATE)
    r1 = etree.SubElement(ins, qn("w:r"))
    t1 = etree.SubElement(r1, qn("w:t")); t1.set(XMLSPACE, "preserve"); t1.text = number
    r2 = etree.SubElement(ins, qn("w:r")); etree.SubElement(r2, qn("w:tab"))
    pPr = p_elem.find(qn("w:pPr"))
    idx = (list(p_elem).index(pPr) + 1) if pPr is not None else 0
    p_elem.insert(idx, ins)


# (marker, old, new) — repoint/clean cross-references, keep prose ----------- #
EDITS = [
    # 5.1.1: governance -> compliance is now 4.2.3
    ("governance as a key enabler",
     "(see section 4.2.4)", "(see section 4.2.3)"),
    # 5.1.1: technical know-how -> technical resources is now 4.2.2
    ("the marketing function requires increasing technical know-how",
     "(see section 4.2.3)", "(see section 4.2.2)"),
    # 5.1.2: three external sources -> two; suppliers folded into 4.1.1
    ("key external sources of inspiration",
     "three key external sources of inspiration that drive AI initiatives: the rapid "
     "progression of AI capability (see Section 4.1.1), market pressure from competitors "
     "and, increasingly, from consumers acting through their own agents (see Section 4.1.2), "
     "and the roadmaps communicated by their software suppliers (see Section 4.1.3).",
     "two key external sources of inspiration that drive AI initiatives: the rapid "
     "progression of AI capability, including the roadmaps communicated by their software "
     "suppliers (see Section 4.1.1), and market pressure from competitors and, increasingly, "
     "from consumers acting through their own agents (see Section 4.1.2)."),
    # 5.1.2: suppliers -> 4.1.1
    ("Managers might follow the AI strategy of their main software vendors",
     "(see Section 4.1.3)", "(see Section 4.1.1)"),
    # 5.1.2: optics/reality gap was deleted from ch4 -> drop dangling pointer
    ("optics can be especially deceiving",
     " (see Section 4.5.3)", ""),
    # 5.1.3: individual-easy/organizational-hard -> survives in 4.2.1
    ("Adopting AI on the individual level seems to be relatively easy",
     "(see Section 4.5.3)", "(see Section 4.2.1)"),
    # 5.1.5: divergent outcomes -> 4.4.4 removed; table renumbered 4->5 (definitions table takes slot 4)
    ("The clearest evidence that this value is managerially mediated",
     "(Section 4.4.4; Table 4)", "(Table 5)"),
    # 5.1.5: self-ref to Observing subsection (renumbered to 5.1.2)
    ("The clearest evidence that this value is managerially mediated",
     "(Section 5.1.3)", "(Section 5.1.2)"),
    # 5.1.5: branding paradox -> now in 4.4.3 Risks
    ("deploying agentic AI to govern the very risks",
     "(Section 4.5.1)", "(Section 4.4.3)"),
    # 5.1.5: hallucinating paradox -> now in 4.4.3 Risks
    ("deploying agentic AI to govern the very risks",
     "(Section 4.5.2)", "(Section 4.4.3)"),
    # 5.1.5: junior paradox -> benefit framing survives in 4.4.1
    ("Deploying agentic AI first on junior tasks threatens the pipeline",
     "(Section 4.5.4)", "(Section 4.4.1)"),
    # 5.2.1: AI champions -> Steering the marketing department is now 4.2.1 (do first)
    ("protecting the AI champions",
     "(Section 4.2.2)", "(Section 4.2.1)"),
    # 5.2.1: data/tooling accessibility -> technical resources is now 4.2.2
    ("making data and tooling accessible enough",
     "(Section 4.2.3)", "(Section 4.2.2)"),
    # 5.2.4: governance with AI -> no 4.5, all in 4.4.3
    ("benchmarking AI output against a human baseline converts risk management",
     "(Sections 4.4.3 and 4.5)", "(Section 4.4.3)"),
    # 5.2.5: external experts/agencies -> technical resources is now 4.2.2
    ("external experts and agencies offer a fast route",
     "(Section 4.2.1)", "(Section 4.2.2)"),
    # 5.2.6: connectors -> customer-facing agents is now 4.3.4
    ("began building connectors so that their products remain reachable",
     "(Sections 4.1.2 and 4.3.1)", "(Sections 4.1.2 and 4.3.4)"),
    # 5.2.6: junior paradox -> 4.4.1
    ("deploying AI first on junior tasks risks eroding the pipeline",
     "(Section 4.5.4)", "(Section 4.4.1)"),
    # 5.3: optics/reality gap deleted from ch4 -> drop dangling pointer (keep prose)
    ("Another limitation lies in the gap between optics and reality",
     " (see section 4.3.1)", ""),
]

# (marker, number) — renumber the bare 5.1.x sub-headings ------------------- #
HEADING_NUMS = [
    ("Observing forces for change", "5.1.2"),
    ("Steering the organizational context", "5.1.3"),
    ("Applying how agentic AI is being used", "5.1.4"),
]


def main():
    check = "--check" in sys.argv
    doc = Document(str(DOCX_PATH))
    used = _used_ids(doc)

    # ---- validate everything first (no mutation) ----
    problems = []
    for marker, old, new in EDITS:
        el = find_elem(doc, marker)
        if el is None:
            problems.append(("PARA NOT FOUND", marker[:45])); continue
        if old not in full_text(el):
            problems.append(("FRAGMENT NOT FOUND", f"{marker[:30]} :: {old[:40]}"))
    for marker, number in HEADING_NUMS:
        el = find_elem(doc, marker)
        if el is None:
            problems.append(("HEADING NOT FOUND", marker[:45]))

    print(f"Validating against: {DOCX_PATH.name}")
    print(f"  {len(EDITS)} cross-ref edits, {len(HEADING_NUMS)} heading renumbers")
    if problems:
        print("\n  MISMATCHES (these would block the save):")
        for kind, what in problems:
            print(f"    [{kind:>18}] {what}")
    else:
        print("  All fragments and headings matched. OK to apply.")

    if check:
        print("\n--check only: no file written.")
        return
    if problems:
        print("\nNOT SAVED - resolve mismatches first (file untouched).")
        return

    # ---- apply ----
    for marker, old, new in EDITS:
        el = find_elem(doc, marker)
        replace_fragment_tracked(el, old, new, used)
    for marker, number in HEADING_NUMS:
        el = find_elem(doc, marker)
        insert_heading_number(el, number, used)

    shutil.copy(DOCX_PATH, BACKUP)
    doc.save(str(DOCX_PATH))
    print(f"\nApplied {len(EDITS)} edits + {len(HEADING_NUMS)} renumbers.")
    print(f"Saved: {DOCX_PATH.name}\nBackup: {BACKUP.name}")


if __name__ == "__main__":
    main()
