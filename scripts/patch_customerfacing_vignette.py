# -*- coding: utf-8 -*-
"""Append the Interviewee 6 vs Interviewee 15 customer-facing comparison to the
stub paragraph 'Customer-facing agents.' in section 4.4.4 (tracked, author 'Claude')."""
from __future__ import annotations
import shutil
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

ROOT      = Path(__file__).resolve().parents[1]
DOCX_PATH = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP    = ROOT / "Thesis Draft - Daan Luttik - MBA.cfvignette-backup.docx"
AUTHOR = "Claude"; DATE = "2026-06-07T13:00:00Z"
XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"

LDQ, RDQ, MD, ELL, APO = "“", "”", "—", "[…]", "’"

PROSE = (
    f"The same divergence separated two consumer-facing deployments at very different stages of "
    f"maturity. Interviewee 6 ran a live agentic chatbot for members that combined service with "
    f"commercial outcomes {MD} the same agent that resolves a membership question can identify and "
    f"execute an upgrade {MD} and attributed roughly tenfold returns to it: {LDQ}{ELL} 10X {ELL} "
    f"Because it{APO}s not two and it{APO}s also not 200.{RDQ} Interviewee 15, pursuing the same broad "
    f"use case, had built a connector that lets customers{APO} own assistants transact with her webshop "
    f"{MD} {LDQ}fetch all my orders {ELL} And then via that connector it actually reorders that order{RDQ} "
    f"{MD} yet described it as deliberately exploratory: {LDQ}the value there now is actually the "
    f"experimenting and staying ahead of that wave.{RDQ} Again the difference lay less in the technology "
    f"than in the conditions around it. Interviewee 6 could deploy at scale because she expanded on an "
    f"existing pre-LLM chatbot ({LDQ}the conversations were already built{RDQ}), held, in her words, "
    f"{LDQ}full trust from my board,{RDQ} and proved the case commercially before scaling {MD} "
    f"{LDQ}it was really because we had commercial success first.{RDQ} Interviewee 15{APO}s connector "
    f"remained an experiment partly because those conditions were still forming; as she put it, "
    f"{LDQ}certain governance is not in it from a brand perspective, and how things look and tone of "
    f"voice {ELL} that is still a challenge.{RDQ}"
)


def _used_ids(doc):
    return {int(el.get(qn("w:id"), 0)) for el in doc.element.body.iter() if el.get(qn("w:id")) is not None}

def main():
    doc = Document(str(DOCX_PATH))
    used = _used_ids(doc)
    nid = (max(used, default=0) + 1)

    # find the stub paragraph: exact short header in 4.4.4
    target = None
    for p in doc.paragraphs:
        if "".join(t.text or "" for t in p._element.iter(qn("w:t"))).strip() == "Customer-facing agents.":
            target = p._element
            break
    assert target is not None, "stub paragraph 'Customer-facing agents.' not found"

    ins = etree.SubElement(target, qn("w:ins"))
    ins.set(qn("w:id"), str(nid)); ins.set(qn("w:author"), AUTHOR); ins.set(qn("w:date"), DATE)
    r = etree.SubElement(ins, qn("w:r"))
    t = etree.SubElement(r, qn("w:t")); t.set(XMLSPACE, "preserve"); t.text = PROSE

    shutil.copy(DOCX_PATH, BACKUP)
    doc.save(str(DOCX_PATH))
    print("Appended customer-facing comparison to §4.4.4 stub.")
    print(f"Saved: {DOCX_PATH}\nBackup: {BACKUP}")

if __name__ == "__main__":
    main()
