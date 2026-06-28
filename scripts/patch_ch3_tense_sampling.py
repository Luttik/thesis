# -*- coding: utf-8 -*-
"""
Chapter 3 (Methodology) wording fix - all tracked, author "Claude".

The methodology was originally written as a proposal (before the study ran).
This patch makes Sections 3.1-3.3 read as completed research:

  1. Sampling term: "purposive sampling (Patton, 2014)" ->
     "theoretical sampling (Charmaz, 2014)" in 3.3.
  2. Tense: remove future "will be" and convert present/proposal-tense
     descriptions of what was actually done to past tense.

Each (para_index, old, new) below targets a substring that lives inside a
single direct-child run and is unique within its paragraph, so the per-run
tracked-replace helper can split it into before / <w:del> / <w:ins> / after.
The inserted run clones the host run's <w:rPr> so the new text matches the
formatting it replaces (matters for the Heading-2 title in para 120).
"""
from __future__ import annotations

import copy
import shutil
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from lxml import etree

ROOT      = Path(__file__).resolve().parents[1]
DOCX_PATH = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP    = ROOT / "Thesis Draft - Daan Luttik - MBA.ch3-backup.docx"

AUTHOR   = "Claude"
DATE     = "2026-06-23T00:00:00Z"
XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"


# --------------------------------------------------------------------------- #
# id + tracked-change helpers
# --------------------------------------------------------------------------- #
def _used_ids(doc) -> set[int]:
    return {int(el.get(qn("w:id"), 0))
            for el in doc.element.body.iter()
            if el.get(qn("w:id")) is not None}


def _nid(used: set[int]) -> int:
    n = max(used, default=0) + 1
    used.add(n)
    return n


def ins_run(text: str, used: set[int], rpr: etree._Element | None = None) -> etree._Element:
    ins = etree.Element(qn("w:ins"))
    ins.set(qn("w:id"), str(_nid(used)))
    ins.set(qn("w:author"), AUTHOR)
    ins.set(qn("w:date"), DATE)
    r = etree.SubElement(ins, qn("w:r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, qn("w:t"))
    t.set(XMLSPACE, "preserve")
    t.text = text
    return ins


def replace_text_tracked(p_elem, old: str, new: str, used: set[int]) -> bool:
    """Tracked find/replace within a single direct-child run.

    Splits the host run into: before-run / <w:del>old</w:del> /
    <w:ins>new</w:ins> / after-run. The inserted run inherits a copy of the
    host run's <w:rPr> so formatting (incl. heading style runs) is preserved.
    """
    for r in p_elem.findall(qn("w:r")):
        t = r.find(qn("w:t"))
        if t is None or not t.text or old not in t.text:
            continue
        rpr = r.find(qn("w:rPr"))
        before, _, after = t.text.partition(old)
        parent = r.getparent()
        idx = list(parent).index(r)
        parts = []
        if before:
            rb = etree.Element(qn("w:r"))
            if rpr is not None:
                rb.append(copy.deepcopy(rpr))
            tb = etree.SubElement(rb, qn("w:t"))
            tb.set(XMLSPACE, "preserve")
            tb.text = before
            parts.append(rb)
        d = etree.Element(qn("w:del"))
        d.set(qn("w:id"), str(_nid(used)))
        d.set(qn("w:author"), AUTHOR)
        d.set(qn("w:date"), DATE)
        rd = etree.SubElement(d, qn("w:r"))
        if rpr is not None:
            rd.append(copy.deepcopy(rpr))
        td = etree.SubElement(rd, qn("w:delText"))
        td.set(XMLSPACE, "preserve")
        td.text = old
        parts.append(d)
        parts.append(ins_run(new, used, rpr))
        if after:
            ra = etree.Element(qn("w:r"))
            if rpr is not None:
                ra.append(copy.deepcopy(rpr))
            ta = etree.SubElement(ra, qn("w:t"))
            ta.set(XMLSPACE, "preserve")
            ta.text = after
            parts.append(ra)
        for j, part in enumerate(parts):
            parent.insert(idx + j, part)
        parent.remove(r)
        return True
    return False


# --------------------------------------------------------------------------- #
# edit list  (para_index, old, new)  -- ordered in document order
# --------------------------------------------------------------------------- #
EDITS = [
    # 3.1 Research approach
    (111, "will be collected and converted", "were collected and converted"),
    (113, "will be used to spark", "was used to spark"),
    # 3.2 Data collection
    (116, "research employs in-depth", "research employed in-depth"),
    (116, "perspective is chosen", "perspective was chosen"),
    (117, "interview is used", "interview was used"),
    (119, "memos are written", "memos were written"),
    (119, "categories are established", "categories were established"),
    (119, "theoretical sampling is applied", "theoretical sampling was applied"),
    (119, "will be augmented", "was augmented"),
    (119, "will be utilized", "were utilized"),
    # 3.3 Sample and sample size
    (120, "Intended sample and sample size", "Sample and sample size"),  # Heading 2
    (121, "field are interviewed", "field were interviewed"),
    (121, "title is chosen", "title was chosen"),
    (121, "they are selected based on knowledge", "they were selected based on knowledge"),
    (122, "purposive ", "theoretical "),
    (122, "Patton, 2014", "Charmaz, 2014"),
    (122, "sampling starts with", "sampling started with"),
    (122, "is used to identify", "was used to identify"),
    (122, "Candidates are selected based on their role", "Candidates were selected based on their role"),
    (122, "universe is already narrow", "universe was already narrow"),
    (122, "criteria are applied", "criteria were applied"),
    (122, "organization are noted", "organization were noted"),
]


def main() -> None:
    doc = Document(str(DOCX_PATH))
    paras = doc.paragraphs
    used = _used_ids(doc)

    failures = []
    for idx, old, new in EDITS:
        ok = replace_text_tracked(paras[idx]._element, old, new, used)
        status = "OK " if ok else "MISS"
        print(f"[{status}] para {idx}: {old!r} -> {new!r}")
        if not ok:
            failures.append((idx, old))

    if failures:
        print(f"\nABORT: {len(failures)} replacement(s) not found; NOT saving.")
        for idx, old in failures:
            print(f"   miss para {idx}: {old!r}")
        sys.exit(1)

    shutil.copy(DOCX_PATH, BACKUP)
    doc.save(str(DOCX_PATH))
    print(f"\nBacked up to: {BACKUP.name}")
    print(f"Applied {len(EDITS)} tracked edits, saved: {DOCX_PATH.name}")


if __name__ == "__main__":
    main()
