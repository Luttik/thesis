# -*- coding: utf-8 -*-
"""
Reword the "inside-out" framing -> "highly dependent on internal conditions and the
configuration in which it is applied" (all tracked, author "Claude").

Also narrows the one place that equated configuration with the harness, so the broad
term (configuration = setup/process/tools around the agent) stays distinct from the
narrow term (harness = the configuration of the agent itself).

All-or-nothing: the file is saved only if every edit succeeds.
"""
from __future__ import annotations

import copy
import shutil
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from lxml import etree

ROOT      = Path(__file__).resolve().parents[1]
DOCX_PATH = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP    = ROOT / "Thesis Draft - Daan Luttik - MBA.reword-backup.docx"

AUTHOR = "Claude"
DATE   = "2026-06-07T12:00:00Z"
XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"


def _used_ids(doc) -> set[int]:
    return {int(el.get(qn("w:id"), 0))
            for el in doc.element.body.iter()
            if el.get(qn("w:id")) is not None}

def _nid(used: set[int]) -> int:
    n = max(used, default=0) + 1; used.add(n); return n

def full_text(p_elem) -> str:
    return "".join(t.text or "" for t in p_elem.iter(qn("w:t")))

def find_elem(doc, marker: str):
    for p in doc.paragraphs:
        if marker in full_text(p._element):
            return p._element
    return None

def _ins_run(text: str, used: set[int]) -> etree._Element:
    ins = etree.Element(qn("w:ins"))
    ins.set(qn("w:id"), str(_nid(used)))
    ins.set(qn("w:author"), AUTHOR)
    ins.set(qn("w:date"), DATE)
    r = etree.SubElement(ins, qn("w:r"))
    t = etree.SubElement(r, qn("w:t")); t.set(XMLSPACE, "preserve"); t.text = text
    return ins


def replace_fragment_tracked(p_elem, old: str, new: str, used: set[int]) -> bool:
    """Tracked replacement of `old` with `new`, robust to the fragment spanning
    multiple direct-child runs (different formatting). Inserts `new` once at the
    point where `old` begins; wraps the matched text in <w:del>."""
    runs = p_elem.findall(qn("w:r"))
    segs = []
    total = ""
    for r in runs:
        t = r.find(qn("w:t"))
        txt = t.text if (t is not None and t.text) else ""
        segs.append((r, txt))
        total += txt
    start = total.find(old)
    if start < 0:
        return False
    end = start + len(old)

    def mk_run(rPr, s):
        nr = etree.Element(qn("w:r"))
        if rPr is not None:
            nr.append(copy.deepcopy(rPr))
        tt = etree.SubElement(nr, qn("w:t")); tt.set(XMLSPACE, "preserve"); tt.text = s
        return nr

    def mk_del(rPr, s):
        d = etree.Element(qn("w:del"))
        d.set(qn("w:id"), str(_nid(used))); d.set(qn("w:author"), AUTHOR); d.set(qn("w:date"), DATE)
        dr = etree.SubElement(d, qn("w:r"))
        if rPr is not None:
            dr.insert(0, copy.deepcopy(rPr))
        dt = etree.SubElement(dr, qn("w:delText")); dt.set(XMLSPACE, "preserve"); dt.text = s
        return d

    pos = 0
    inserted = False
    for r, txt in segs:
        r_start, r_end = pos, pos + len(txt)
        pos = r_end
        if not txt or r_end <= start or r_start >= end:
            continue  # untouched run
        rPr = r.find(qn("w:rPr"))
        ls = max(start, r_start) - r_start
        le = min(end, r_end) - r_start
        before, deleted, after = txt[:ls], txt[ls:le], txt[le:]
        parent = r.getparent(); idx = list(parent).index(r)
        parts = []
        if before:
            parts.append(mk_run(rPr, before))
        if not inserted:
            parts.append(_ins_run(new, used)); inserted = True
        if deleted:
            parts.append(mk_del(rPr, deleted))
        if after:
            parts.append(mk_run(rPr, after))
        for j, part in enumerate(parts):
            parent.insert(idx + j, part)
        parent.remove(r)
    return inserted


# (marker, old, new) -------------------------------------------------------- #
DQ = "“"; DQR = "”"; MD = "—"; APO = "’"

EDITS = [
    # 4.4.4 - synthesis sentence
    ("contrasts point to the chapter",
     "is an inside-out process, shaped more by what an organization does with the technology than by which technology it adopts.",
     "is highly dependent on internal conditions and the configuration in which the technology is applied, rather than on which technology is adopted."),
    # 4.4.4 - keep configuration (broad) distinct from harness (agent-level)
    ("contrasts point to the chapter",
     f"the difference in the configuration {MD} the {DQ}harness{DQR}",
     f"the difference in the configuration of the agent itself {MD} the {DQ}harness{DQR}"),
    # 5.2 - practical implications opener
    ("practical implications of this study concern",
     "is an inside-out, managerial achievement rather than a procurement decision",
     "depends far more on internal conditions and the configuration in which it is applied than on the procurement decision"),
    # 5.3 - limitations
    ("would be better positioned to assess where",
     "the inside-out logic identified in section 4",
     "the dependence on internal conditions and configuration identified in section 4"),
    # 6 - headline conclusion
    ("Drawing on seventeen interviews",
     "is an inside-out, managerial accomplishment",
     "is highly dependent on internal conditions and the configuration in which it is applied"),
    # 6 - contribution statement
    ("process account of inside-out value creation",
     "a grounded, process account of inside-out value creation, together with",
     "a grounded, process account of how internal conditions and the configuration in which agentic AI is applied shape value creation, together with"),
    # 5.1 - optional tighten (same meaning, aligned vocabulary)
    ("locating the determinants of value inside the organization",
     "the determinants of value inside the organization rather than in the technology itself",
     f"the determinants of value in the organization{APO}s internal conditions and the configuration in which the technology is applied rather than in the technology itself"),
]


def main():
    doc  = Document(str(DOCX_PATH))
    used = _used_ids(doc)

    results = []
    for marker, old, new in EDITS:
        el = find_elem(doc, marker)
        if el is None:
            results.append((marker, "PARA NOT FOUND"))
            continue
        ok = replace_fragment_tracked(el, old, new, used)
        results.append((marker, "ok" if ok else "FRAGMENT NOT MATCHED"))

    print("Edit results:")
    for marker, status in results:
        print(f"  [{status:>18}]  {marker}")

    if all(s == "ok" for _, s in results):
        shutil.copy(DOCX_PATH, BACKUP)
        doc.save(str(DOCX_PATH))
        print(f"\nAll edits applied. Saved: {DOCX_PATH}\nBackup: {BACKUP}")
    else:
        print("\nNOT SAVED - one or more edits failed; file left untouched.")


if __name__ == "__main__":
    main()
