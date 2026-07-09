# -*- coding: utf-8 -*-
"""
Fix paragraph 51 (Executive Summary), which lost its tracked-change status
somewhere in the pipeline: "empirical works" -> "empirical accounts" never
landed at all (plain text still reads "works"), and "And in doing so" ->
"In doing so" landed as correct final CONTENT but got silently baked into
plain text (not trackable/reviewable in Word).

Rebuilds both as clean, minimal tracked changes from the start:
  - r12 'In doing so' (currently plain) -> del('And in') + ins('In') + plain(' doing so')
  - r15 'empirical works' (currently plain) -> plain('empirical ') + del('works') + ins('accounts')
"""
from __future__ import annotations

import copy
import shutil
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from lxml import etree

ROOT   = Path(__file__).resolve().parents[1]
DOCX   = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP = ROOT / "Thesis Draft - Daan Luttik - MBA.pre-para51fix-backup.docx"

AUTHOR, DATE = "Claude", "2026-07-09T00:00:00Z"
XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"


def clone_rpr(r_el):
    rpr = r_el.find(qn("w:rPr"))
    return copy.deepcopy(rpr) if rpr is not None else None


def _used_ids(doc):
    return {int(el.get(qn("w:id"), 0)) for el in doc.element.body.iter() if el.get(qn("w:id")) is not None}


def _nid(used):
    n = max(used, default=0) + 1
    used.add(n)
    return n


def mk_plain(text, rpr):
    r = etree.Element(qn("w:r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, qn("w:t")); t.set(XMLSPACE, "preserve"); t.text = text
    return r


def mk_del(text, rpr, used):
    d = etree.Element(qn("w:del"))
    d.set(qn("w:id"), str(_nid(used))); d.set(qn("w:author"), AUTHOR); d.set(qn("w:date"), DATE)
    r = etree.SubElement(d, qn("w:r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    dt = etree.SubElement(r, qn("w:delText")); dt.set(XMLSPACE, "preserve"); dt.text = text
    return d


def mk_ins(text, rpr, used):
    ins = etree.Element(qn("w:ins"))
    ins.set(qn("w:id"), str(_nid(used))); ins.set(qn("w:author"), AUTHOR); ins.set(qn("w:date"), DATE)
    r = etree.SubElement(ins, qn("w:r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, qn("w:t")); t.set(XMLSPACE, "preserve"); t.text = text
    return ins


def main():
    doc = Document(str(DOCX))
    used = _used_ids(doc)
    p = doc.paragraphs[51]._element
    runs = p.findall(qn("w:r"))

    fixed = []
    for r in runs:
        t = r.find(qn("w:t"))
        if t is None or not t.text:
            continue
        rpr = clone_rpr(r)
        parent = r.getparent()
        idx = list(parent).index(r)

        if t.text == "In doing so":
            replacement = [
                mk_del("And in", rpr, used),
                mk_ins("In", rpr, used),
                mk_plain(" doing so", rpr),
            ]
            for k, node in enumerate(replacement):
                parent.insert(idx + k, node)
            parent.remove(r)
            fixed.append("And in doing so -> In doing so")

        elif t.text == "empirical works":
            replacement = [
                mk_plain("empirical ", rpr),
                mk_del("works", rpr, used),
                mk_ins("accounts", rpr, used),
            ]
            for k, node in enumerate(replacement):
                parent.insert(idx + k, node)
            parent.remove(r)
            fixed.append("empirical works -> empirical accounts")

    print("Fixed:", fixed)
    if len(fixed) != 2:
        print("ABORT: expected to fix exactly 2 spots, aborting without saving.")
        return

    shutil.copy(DOCX, BACKUP)
    doc.save(str(DOCX))
    print(f"Backed up to: {BACKUP.name}\nSaved: {DOCX.name}")


if __name__ == "__main__":
    main()
