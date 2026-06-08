# -*- coding: utf-8 -*-
"""
Reference list + citation cleanup (clean, non-tracked; §7 is in the rewrite zone):
  - §7 heading: drop the "(not all papers are currently used…)" note.
  - Add Teece (1997) and Teece (2007) entries (cited by the new §5.1.2/§5.1.3).
  - Remove the unverifiable "Ellström et al., 2021" citation from §5.1.2/§5.1.3
    (lean on Teece + Hanelt, which have entries).
  - Fix malformed APA entries: Acharya (author order, casing, IEEE), Krizhevsky
    (Chicago -> APA); remove the duplicate Huang & Rust (2020) (in-text cites 2021).
  - Correct in-text "Jain & Eastman, 2024" -> "Jain et al., 2024" (entry has 3 authors).
"""
from __future__ import annotations

import shutil
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from lxml import etree

from patch_sec44_inside_out import find_elem, insert_before, XMLSPACE
from patch_sec51_discussion import clean_body

ROOT      = Path(__file__).resolve().parents[1]
DOCX_PATH = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP    = ROOT / "Thesis Draft - Daan Luttik - MBA.refs-backup.docx"

EN = "–"  # –


def clean_ref_para(segments):
    """Clean reference entry: hanging indent 720/720 + white highlight; italic per flag."""
    p = etree.Element(qn("w:p"))
    pPr = etree.SubElement(p, qn("w:pPr"))
    ind = etree.SubElement(pPr, qn("w:ind")); ind.set(qn("w:left"), "720"); ind.set(qn("w:hanging"), "720")
    rPr = etree.SubElement(pPr, qn("w:rPr"))
    etree.SubElement(rPr, qn("w:highlight")).set(qn("w:val"), "white")
    for text, italic in segments:
        r = etree.SubElement(p, qn("w:r"))
        rpr = etree.SubElement(r, qn("w:rPr"))
        if italic:
            etree.SubElement(rpr, qn("w:i")); etree.SubElement(rpr, qn("w:iCs"))
        etree.SubElement(rpr, qn("w:highlight")).set(qn("w:val"), "white")
        t = etree.SubElement(r, qn("w:t")); t.set(XMLSPACE, "preserve"); t.text = text
    return p


TEECE_1997 = [
    ("Teece, D. J., Pisano, G., & Shuen, A. (1997). Dynamic capabilities and strategic "
     "management. ", False),
    ("Strategic Management Journal, 18", True),
    (f"(7), 509{EN}533.", False),
]
TEECE_2007 = [
    ("Teece, D. J. (2007). Explicating dynamic capabilities: The nature and "
     "microfoundations of (sustainable) enterprise performance. ", False),
    ("Strategic Management Journal, 28", True),
    (f"(13), 1319{EN}1350. https://doi.org/10.1002/smj.640", False),
]
ACHARYA = [
    ("Acharya, D. B., Kuppan, K., & Divya, B. (2025). Agentic AI: Autonomous intelligence "
     "for complex goals—A comprehensive survey. ", False),
    ("IEEE Access", True),
    (".", False),
]
KRIZHEVSKY = [
    ("Krizhevsky, A., Sutskever, I., & Hinton, G. E. (2012). ImageNet classification with "
     "deep convolutional neural networks. ", False),
    ("Advances in Neural Information Processing Systems, 25", True),
    (f", 1097{EN}1105.", False),
]

S512_FIX = (
    "The model’s first stage locates value creation before any technology is "
    "deployed, in how managers observe a fast-moving environment. Across the data, "
    "managers attended to three external signals: the rapid progression of AI capability "
    "(Section 4.1.1), market pressure from competitors and, increasingly, from consumers "
    "acting through their own agents (Section 4.1.2), and the roadmaps communicated by "
    "their software suppliers (Section 4.1.3). Reading these signals corresponds closely "
    "to what the dynamic-capabilities literature calls *sensing* — the "
    "identification of opportunities and threats in a changing environment (Teece, 1997, "
    "2007). In answering the calls for research into agentic AI in marketing (Kim, 2025; "
    "Mogaji & Jain, 2024), the study’s first observation is that managers are, on the "
    "whole, competent sensors: the arrival and relevance of agentic AI was widely and "
    "similarly perceived."
)
S513_FIX = (
    "If observing identifies the opportunity, steering is where value is won or lost. "
    "Section 5.1.1 established that the organizational conditions surrounding agentic AI "
    "— literacy, data and infrastructure, leadership, and governance — matter "
    "even more than in earlier waves of digital transformation; the present contribution "
    "concerns how managers act on those conditions. The study identifies a three-part "
    "repertoire: managers *reshape* conditions they control, *leverage* conditions that "
    "are already favorable, and *navigate* conditions they cannot change by working "
    "within them. This gives microfoundational, marketing-specific content to the "
    "*seizing* and *reconfiguring* activities that dynamic-capabilities theory names but "
    "tends to treat at the level of the firm (Teece, 1997, 2007; Hanelt et al., 2021)."
)


def replace_para(doc, anchor, new_para):
    el = find_elem(doc, anchor)
    assert el is not None, f"anchor not found: {anchor!r}"
    insert_before(el, [new_para])
    el.getparent().remove(el)


def main():
    shutil.copy(DOCX_PATH, BACKUP)
    doc = Document(str(DOCX_PATH))
    body = doc.part._element

    # 1. §7 heading: drop the note --------------------------------------- #
    h7 = find_elem(doc, "not all papers are currently used")
    assert h7 is not None, "§7 heading not found"
    wts = h7.findall(".//" + qn("w:t"))
    # wts = ["7.", "References (not all papers ...)"] ; set title to "References"
    wts[-1].text = "References"
    print("1. §7 heading note removed")

    # 2. add Teece 1997 + 2007 before the Vaid entry --------------------- #
    vaid = find_elem(doc, "Vaid, S., Puntoni")
    assert vaid is not None, "Vaid anchor not found"
    insert_before(vaid, [clean_ref_para(TEECE_1997), clean_ref_para(TEECE_2007)])
    print("2. added Teece (1997) + Teece (2007)")

    # 3. fix Acharya + Krizhevsky entries -------------------------------- #
    replace_para(doc, "Acharya et al., D. B.", clean_ref_para(ACHARYA))
    replace_para(doc, "Krizhevsky, Alex, Ilya Sutskever", clean_ref_para(KRIZHEVSKY))
    print("3. fixed Acharya + Krizhevsky entries")

    # 4. remove duplicate Huang & Rust (2020) (in-text cites 2021) ------- #
    h2020 = find_elem(doc, "Huang, M., & Rust, R. (2020)")
    assert h2020 is not None, "Huang 2020 anchor not found"
    h2020.getparent().remove(h2020)
    print("4. removed duplicate Huang & Rust (2020)")

    # 5. drop Ellström citation from §5.1.2 / §5.1.3 --------------------- #
    replace_para(doc, "The model’s first stage locates value creation", clean_body(S512_FIX))
    replace_para(doc, "If observing identifies the opportunity, steering is where value", clean_body(S513_FIX))
    print("5. removed unverifiable Ellström citation from §5.1.2/§5.1.3")

    # 6. correct "Jain & Eastman, 2024" -> "Jain et al., 2024" ----------- #
    n = 0
    for t in body.iter(qn("w:t")):
        if t.text and "Jain & Eastman, 2024" in t.text:
            t.text = t.text.replace("Jain & Eastman, 2024", "Jain et al., 2024"); n += 1
    print(f"6. corrected 'Jain & Eastman' -> 'Jain et al.' in {n} run(s)")

    doc.save(str(DOCX_PATH))
    print(f"\nSaved: {DOCX_PATH}\nBackup: {BACKUP}")


if __name__ == "__main__":
    main()
