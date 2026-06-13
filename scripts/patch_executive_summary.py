# -*- coding: utf-8 -*-
"""
Insert a one-page Executive Summary after the Table of Contents (SDT) and before
the Introduction, as a tracked change (author "Claude").

Placement: the body order is  ... declaration -> TOC(sdt) -> [sectPr para] -> "1. Introduction".
We insert the Executive Summary heading + body paragraphs immediately AFTER the TOC sdt
(i.e. before the section-break paragraph), so it sits after the TOC and the existing
section break still starts the Introduction on a fresh page. The heading carries
<w:pageBreakBefore/> so the summary itself opens on its own page.

Structure follows the Nyenrode "Executive Summary - one-page maximum" checklist:
purpose/RQ, method, main findings, practical implications, theoretical implications,
limitations, originality.
"""
from __future__ import annotations

import copy
import shutil
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "Thesis Draft - Daan Luttik - MBA - copy from 2026-06-13.docx"
BACKUP = ROOT / "Thesis Draft - Daan Luttik - MBA - copy from 2026-06-13.execsum-backup.docx"

AUTHOR = "Claude"
DATE = "2026-06-13T00:00:00Z"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"


def _used_ids(doc) -> set:
    return {int(el.get(qn("w:id"), 0))
            for el in doc.element.body.iter()
            if el.get(qn("w:id")) is not None}


def _nid(used: set) -> int:
    n = max(used, default=0) + 1
    used.add(n)
    return n


def _ins_attrs(el, used):
    el.set(qn("w:id"), str(_nid(used)))
    el.set(qn("w:author"), AUTHOR)
    el.set(qn("w:date"), DATE)


def make_para(runs, used, *, heading=False, page_break=False):
    """runs: list of (text, bold, italic). Whole paragraph tracked-inserted
    (runs wrapped in <w:ins>, and the paragraph mark marked inserted too)."""
    p = etree.Element(qn("w:p"))
    pPr = etree.SubElement(p, qn("w:pPr"))
    if heading:
        ps = etree.SubElement(pPr, qn("w:pStyle"))
        ps.set(qn("w:val"), "Heading1")
    if page_break:
        etree.SubElement(pPr, qn("w:pageBreakBefore"))
    if not heading:
        # single line spacing so the summary fits one page (body is double-spaced)
        sp = etree.SubElement(pPr, qn("w:spacing"))
        sp.set(qn("w:line"), "240")
        sp.set(qn("w:lineRule"), "auto")
    # tracked paragraph mark
    rPr = etree.SubElement(pPr, qn("w:rPr"))
    ins_mark = etree.SubElement(rPr, qn("w:ins"))
    _ins_attrs(ins_mark, used)
    # the runs, all inside one <w:ins>
    ins = etree.SubElement(p, qn("w:ins"))
    _ins_attrs(ins, used)
    for text, bold, italic in runs:
        r = etree.SubElement(ins, qn("w:r"))
        if bold or italic:
            r_rpr = etree.SubElement(r, qn("w:rPr"))
            if bold:
                etree.SubElement(r_rpr, qn("w:b"))
                etree.SubElement(r_rpr, qn("w:bCs"))
            if italic:
                etree.SubElement(r_rpr, qn("w:i"))
                etree.SubElement(r_rpr, qn("w:iCs"))
        t = etree.SubElement(r, qn("w:t"))
        t.set(XMLSPACE, "preserve")
        t.text = text
    return p


# ---- content -------------------------------------------------------------- #
APOS = "’"  # right single quote


def B(t):  # bold label
    return (t, True, False)


def N(t):  # normal
    return (t, False, False)


def I(t):  # italic
    return (t, False, True)


HEADING = [N("Executive Summary")]

PARAS = [
    # 1. Purpose & research question
    [
        B("Purpose and research question. "),
        N("Generative AI has become central to marketing, which together with sales is projected to "
          "capture roughly a third of AI" + APOS + "s economic value (Mayer et al., 2025). Yet most "
          "marketing AI still works as a question-and-answer tool. A newer category, "),
        I("agentic AI"),
        N(", can pursue goals autonomously across complex, multi-step tasks and so promises to perform "
          "the work itself. How managers turn that promise into value is largely unexplored, and scholars "
          "have issued explicit calls for firm-level evidence (Kim, 2025; Mogaji & Jain, 2024; Jain et al., "
          "2024). This study therefore asks: "),
        I("How do marketing managers create value with agentic AI?"),
        N(" Three sub-questions examine how managers identify and translate opportunities, adopt agentic AI "
          "within their organizations, and manage the benefits, sacrifices, and risks it brings."),
    ],
    # 2. Method
    [
        B("Method. "),
        N("The study applies constructivist grounded theory (Charmaz, 2014), an exploratory qualitative "
          "approach suited to an emerging phenomenon. Seventeen in-depth, semi-structured interviews with "
          "marketing managers and AI experts were analyzed iteratively through initial, focused, and "
          "theoretical coding, with theoretical sampling continued until saturation. Value theory (Almquist "
          "et al., 2016; Woodside et al., 2008) served as a sensitizing concept."),
    ],
    # 3. Main findings
    [
        B("Main findings. "),
        N("Value is created not by adopting agentic AI but by the managerial work surrounding it. The "
          "study" + APOS + "s central contribution is a process model that links five elements: "),
        I("observing"),
        N(" external conditions (the progression of AI, market pressure, and supplier roadmaps); "),
        I("navigating"),
        N(" the organizational conditions that enable or constrain action; "),
        I("steering"),
        N(" the organization by reshaping, leveraging, and navigating those conditions; "),
        I("applying"),
        N(" agentic AI through specific use cases and a deliberately engineered configuration, the "),
        I("harness"),
        N("; and the resulting "),
        I("value outcomes"),
        N(", understood as a managed portfolio of benefits, sacrifices, and risks. Identical use cases "
          "produced divergent outcomes across firms; the difference lay in the managerial work and the "
          "configuration, not the technology. A pattern of paradoxes runs throughout: the technology that "
          "creates a risk also supplies the means to govern it."),
    ],
    # 4. Practical implications
    [
        B("Practical implications. "),
        N("Managers should treat adoption as a change program rather than a procurement: build the enabling "
          "conditions and lead the change; consciously choose a follow (parity) or a differentiate posture; "
          "start from the workflow and engineer the configuration; govern AI with AI, calibrated to the cost "
          "of error; resource and source capability strategically; and look outward to consumers" + APOS +
          " own agents and to the junior-talent pipeline. Appendix B turns these into an operational checklist."),
    ],
    # 5. Theoretical implications
    [
        B("Theoretical implications. "),
        N("The findings extend digital-transformation theory (Enholm et al., 2022; Vidal et al., 2022; "
          "Gebauer et al., 2020); notably, governance shifts from an enabler to an inhibitor of adoption. The "
          "study also specifies the configuration through which an agentic system becomes a value-creating "
          "actor (Orlikowski, 2000; Vargo & Lusch, 2017)."),
    ],
    # 6. Limitations
    [
        B("Limitations. "),
        N("As a qualitative study of a fast-moving technology, the findings are transferable but "
          "context-bound, and observations tied to specific use cases may date quickly. The study relies "
          "exclusively on self-reported interview data."),
    ],
    # 7. Originality
    [
        B("Originality. "),
        N("This is one of the first grounded empirical accounts of value creation with agentic AI in "
          "marketing. It moves beyond the field" + APOS + "s prevailing focus on content generation and "
          "offers a process model, together with an analytical vocabulary (reshaping, leveraging, and "
          "navigating; the harness; and value as a managed portfolio), for understanding the managerial work "
          "that turns agentic AI into value."),
    ],
]


def find_toc_sdt(doc):
    body = doc.element.body
    for el in body:
        if etree.QName(el).localname == "sdt":
            txt = "".join(t.text or "" for t in el.iter(qn("w:t")))
            if "Contents" in txt and "Introduction" in txt:
                return el
    return None


def main():
    shutil.copy2(DOCX, BACKUP)
    doc = Document(str(DOCX))
    used = _used_ids(doc)

    toc = find_toc_sdt(doc)
    if toc is None:
        raise SystemExit("Could not locate the TOC sdt")
    body = doc.element.body
    anchor_idx = list(body).index(toc)

    new_paras = [make_para(HEADING, used, heading=True, page_break=True)]
    for runs in PARAS:
        new_paras.append(make_para(runs, used))

    for i, p in enumerate(new_paras):
        body.insert(anchor_idx + 1 + i, p)

    wc = sum(len(("".join(t for t, *_ in runs)).split()) for runs in PARAS)
    try:
        doc.save(str(DOCX))
        print(f"Inserted Executive Summary IN PLACE: 1 heading + {len(PARAS)} paragraphs, ~{wc} words.")
        print(f"Backup written to: {BACKUP.name}")
    except PermissionError:
        out = DOCX.with_name(DOCX.stem + " (with exec summary).docx")
        doc.save(str(out))
        print("ORIGINAL IS LOCKED (open in Word). Wrote review copy instead:")
        print(f"  {out.name}")
        print(f"Inserted Executive Summary: 1 heading + {len(PARAS)} paragraphs, ~{wc} words.")


if __name__ == "__main__":
    main()
