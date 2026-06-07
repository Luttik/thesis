# -*- coding: utf-8 -*-
"""
Connect claims to literature (all tracked, author "Claude").

Targeted scope agreed with the user; grey literature included, clearly framed.

Edits
-----
1. Reference year fix : in-text "(Huang & Rust, 2020)" -> "(Huang & Rust, 2021)"
                        (the cite is itself an unaccepted Claude <w:ins>, so the
                        year is corrected in place rather than re-tracked).
2. §2.2  across-process: append "(Vaid et al., 2025; Prasanna & Kushwaha, 2025)"
                        to the previously uncited "AI can contribute across the
                        marketing process rather than only within communications."
3. §2.4  co-creation  : insert a foundational service-dominant-logic sentence
                        (Vargo & Lusch, 2017) before the Kaartemo/Leone sentences.
4. §5.1.2 config-in-use: (a) add Vargo & Lusch to the co-creation parenthetical;
                        (b) insert a practice-lens grounding sentence (Orlikowski, 2000).
5. §5.1.1 binding-constraint: insert a triangulation sentence after the
                        complementary-assets cite (Vidal et al., 2022; Bughin, 2024;
                        Wharton Human-AI Research & GBK Collective, 2025).
6. Reference list     : add tracked entries for Bughin (2024), Huang & Rust (2021,
                        corrected), Orlikowski (2000), Prasanna & Kushwaha (2025),
                        Vaid et al. (2025), Vargo & Lusch (2017), and Wharton (2025),
                        each placed alphabetically.
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
BACKUP    = ROOT / "Thesis Draft - Daan Luttik - MBA.litconnect-backup.docx"

AUTHOR   = "Claude"
DATE     = "2026-06-07T00:00:00Z"
W        = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"

EMDASH = "—"   # —
RSQUO  = "’"   # ’
LSQUO  = "‘"   # ‘
NDASH  = "–"   # –


# --------------------------------------------------------------------------- #
# id / text helpers
# --------------------------------------------------------------------------- #
def _used_ids(doc) -> set:
    return {int(el.get(qn("w:id"), 0))
            for el in doc.element.body.iter()
            if el.get(qn("w:id")) is not None}

def _nid(used: set) -> int:
    n = max(used, default=0) + 1
    used.add(n)
    return n

def full_text(p_elem) -> str:
    return "".join(t.text or "" for t in p_elem.iter(qn("w:t")))

def find_para(doc, marker: str):
    for p in doc.paragraphs:
        if marker in full_text(p._element):
            return p._element
    return None


# --------------------------------------------------------------------------- #
# tracked-change builders
# --------------------------------------------------------------------------- #
def _mk_run(text: str, rpr_src) -> etree._Element:
    r = etree.Element(qn("w:r"))
    if rpr_src is not None:
        r.append(copy.deepcopy(rpr_src))
    t = etree.SubElement(r, qn("w:t"))
    t.set(XMLSPACE, "preserve")
    t.text = text
    return r

def _wrap_ins(run: etree._Element, used: set) -> etree._Element:
    ins = etree.Element(qn("w:ins"))
    ins.set(qn("w:id"), str(_nid(used)))
    ins.set(qn("w:author"), AUTHOR)
    ins.set(qn("w:date"), DATE)
    ins.append(run)
    return ins


def insert_after_anchor(p_elem, anchor: str, text: str, used: set) -> bool:
    """Insert `text` (tracked, author Claude) immediately after `anchor`.

    Works whether the anchor run is a direct child of <w:p> or nested inside a
    <w:ins>/<w:hyperlink>. If the anchor run already sits inside a <w:ins>, the
    inserted run is added plain (it inherits that insertion); otherwise it is
    wrapped in its own <w:ins>.
    """
    for r in p_elem.iter(qn("w:r")):
        t = r.find(qn("w:t"))
        if t is None or not t.text or anchor not in t.text:
            continue
        before, _, after = t.text.partition(anchor)
        rpr = r.find(qn("w:rPr"))
        parent = r.getparent()
        idx = list(parent).index(r)

        t.text = before + anchor                       # truncate original run

        new_nodes = []
        ins_run = _mk_run(text, rpr)
        if parent.tag == qn("w:ins"):
            new_nodes.append(ins_run)                  # inherit enclosing insertion
        else:
            new_nodes.append(_wrap_ins(ins_run, used))
        if after:
            after_run = _mk_run(after, rpr)
            if parent.tag == qn("w:ins"):
                new_nodes.append(after_run)
            else:
                # keep `after` as plain original text (not tracked)
                new_nodes.append(after_run)
        for j, node in enumerate(new_nodes):
            parent.insert(idx + 1 + j, node)
        return True
    return False


def edit_run_text_inplace(p_elem, old: str, new: str) -> bool:
    """Replace `old` with `new` inside whatever run holds it, no tracking.

    Used only to correct an already-unaccepted Claude insertion (the year in
    "(Huang & Rust, 2020)"). Searches nested runs too.
    """
    for r in p_elem.iter(qn("w:r")):
        t = r.find(qn("w:t"))
        if t is not None and t.text and old in t.text:
            t.text = t.text.replace(old, new)
            return True
    return False


def insert_before(anchor_p, new_p) -> None:
    parent = anchor_p.getparent()
    parent.insert(list(parent).index(anchor_p), new_p)

def insert_after(anchor_p, new_p) -> None:
    parent = anchor_p.getparent()
    parent.insert(list(parent).index(anchor_p) + 1, new_p)


def ref_para(segments, used: set) -> etree._Element:
    """Build a tracked-inserted reference-list paragraph.

    segments: list of (text, italic) tuples. House style: hanging indent
    720/720, every run highlighted white, journal+volume italic.
    """
    p = etree.Element(qn("w:p"))
    pPr = etree.SubElement(p, qn("w:pPr"))
    ind = etree.SubElement(pPr, qn("w:ind"))
    ind.set(qn("w:left"), "720")
    ind.set(qn("w:hanging"), "720")
    rPr = etree.SubElement(pPr, qn("w:rPr"))
    insmark = etree.SubElement(rPr, qn("w:ins"))
    insmark.set(qn("w:id"), str(_nid(used)))
    insmark.set(qn("w:author"), AUTHOR)
    insmark.set(qn("w:date"), DATE)
    hl = etree.SubElement(rPr, qn("w:highlight"))
    hl.set(qn("w:val"), "white")

    ins = etree.SubElement(p, qn("w:ins"))
    ins.set(qn("w:id"), str(_nid(used)))
    ins.set(qn("w:author"), AUTHOR)
    ins.set(qn("w:date"), DATE)
    for text, italic in segments:
        r = etree.SubElement(ins, qn("w:r"))
        rpr = etree.SubElement(r, qn("w:rPr"))
        if italic:
            etree.SubElement(rpr, qn("w:i"))
            etree.SubElement(rpr, qn("w:iCs"))
        h = etree.SubElement(rpr, qn("w:highlight"))
        h.set(qn("w:val"), "white")
        t = etree.SubElement(r, qn("w:t"))
        t.set(XMLSPACE, "preserve")
        t.text = text
    return p


# --------------------------------------------------------------------------- #
# content
# --------------------------------------------------------------------------- #
SDL_SENTENCE = (
    f" Service-dominant logic provides the foundational lens here: value is co-created by "
    f"multiple actors{EMDASH}always including the beneficiary{EMDASH}through the integration of "
    f"operant resources, and is determined in use and in context rather than embedded in a "
    f"product or delivered by a single firm (Vargo & Lusch, 2017)."
)

PRACTICE_LENS_SENTENCE = (
    f" The practice-lens tradition makes the same point: a technology{RSQUO}s structures and "
    f"effects are emergent in its use rather than embodied in the artifact, so that what matters "
    f"is the return on the use of a technology, not the technology itself (Orlikowski, 2000)."
)

TRIANGULATION_SENTENCE = (
    "Recent large-sample studies of AI adoption reinforce this: AI architecture is found to be "
    f"necessary but not sufficient, with organizational readiness {EMDASH} people and processes "
    f"{EMDASH} rather than technical capacity the binding constraint on value (Vidal et al., 2022; "
    "Bughin, 2024; Wharton Human-AI Research & GBK Collective, 2025). "
)

REFS = {
    "Bughin": [
        (f"Bughin, J. (2024). Inside the successful make-up of {LSQUO}AI-first{RSQUO} organisations. ", False),
        ("Journal of AI, Robotics & Workplace Automation, 3", True),
        ("(3), 211" + NDASH + "219. https://doi.org/10.69554/WPNS5765", False),
    ],
    "Huang2021": [
        ("Huang, M.-H., & Rust, R. T. (2021). A strategic framework for artificial intelligence in marketing. ", False),
        ("Journal of the Academy of Marketing Science, 49", True),
        ("(1), 30" + NDASH + "50. https://doi.org/10.1007/s11747-020-00749-9", False),
    ],
    "Orlikowski": [
        ("Orlikowski, W. J. (2000). Using technology and constituting structures: A practice lens for studying technology in organizations. ", False),
        ("Organization Science, 11", True),
        ("(4), 404" + NDASH + "428. https://doi.org/10.1287/orsc.11.4.404.14600", False),
    ],
    "Prasanna": [
        ("Prasanna, A., & Kushwaha, B. P. (2025). Transforming marketing landscapes: A systematic literature review of generative AI using the TCCM model framework. ", False),
        ("Management Review Quarterly", True),
        (". Advance online publication. https://doi.org/10.1007/s11301-025-00486-9", False),
    ],
    "Vaid": [
        (f"Vaid, S., Puntoni, S., Honig, B., & Michael, K. (2025). When attention is all marketers need{EMDASH}Artificial intelligence in marketing [Editorial]. ", False),
        ("IEEE Transactions on Technology and Society, 6", True),
        ("(3), 242" + NDASH + "249. https://doi.org/10.1109/TTS.2025.3568113", False),
    ],
    "Vargo": [
        ("Vargo, S. L., & Lusch, R. F. (2017). Service-dominant logic 2025. ", False),
        ("International Journal of Research in Marketing, 34", True),
        ("(1), 46" + NDASH + "67. https://doi.org/10.1016/j.ijresmar.2016.11.001", False),
    ],
    "Wharton": [
        ("Wharton Human-AI Research & GBK Collective. (2025). ", False),
        ("Accountable acceleration: Gen AI fast-tracks into the enterprise", True),
        (" (Year three full report). The Wharton School, University of Pennsylvania.", False),
    ],
}


def main():
    shutil.copy(DOCX_PATH, BACKUP)
    doc  = Document(str(DOCX_PATH))
    used = _used_ids(doc)
    results = []

    # 1. Huang year fix (in-place on the unaccepted Claude insertion) -------- #
    p22 = find_para(doc, "across the marketing process rather than only within")
    assert p22 is not None, "§2.2 paragraph not found"
    ok = edit_run_text_inplace(p22, "(Huang & Rust, 2020)", "(Huang & Rust, 2021)")
    results.append(("1. Huang & Rust 2020->2021 (in-text)", ok))

    # 2. §2.2 across-process citation --------------------------------------- #
    ok = insert_after_anchor(
        p22, "communications",
        " (Vaid et al., 2025; Prasanna & Kushwaha, 2025)", used)
    results.append(("2. §2.2 Vaid + Prasanna & Kushwaha", ok))

    # 3. §2.4 service-dominant-logic foundation ----------------------------- #
    p24 = find_para(doc, "increasingly participate in service and marketing interactions")
    assert p24 is not None, "§2.4 co-creation paragraph not found"
    ok = insert_after_anchor(
        p24, "increasingly participate in service and marketing interactions.",
        SDL_SENTENCE, used)
    results.append(("3. §2.4 Vargo & Lusch (SD-logic foundation)", ok))

    # 4. §5.1.2 config-in-use ----------------------------------------------- #
    p512 = find_para(doc, "value cannot be read off the technology")
    assert p512 is not None, "§5.1.2 paragraph not found"
    ok_b = insert_after_anchor(
        p512, "integrated with the system in practice.",
        PRACTICE_LENS_SENTENCE, used)
    results.append(("4b. §5.1.2 Orlikowski practice-lens sentence", ok_b))
    ok_a = insert_after_anchor(
        p512, "serving as a passive instrument (",
        "Vargo & Lusch, 2017; ", used)
    results.append(("4a. §5.1.2 Vargo & Lusch in co-creation cite", ok_a))

    # 5. §5.1.1 binding-constraint triangulation ---------------------------- #
    p511 = find_para(doc, "mediated by complementary assets rather than realized automatically")
    assert p511 is not None, "§5.1.1 paragraph not found"
    ok = insert_after_anchor(
        p511, "Holmström, 2022; Teece, 1986). ",
        TRIANGULATION_SENTENCE, used)
    results.append(("5. §5.1.1 Vidal + Bughin + Wharton triangulation", ok))

    # 6. reference-list entries (alphabetical, tracked) --------------------- #
    ref_plan = [
        ("Bughin",     "before", "Burkhardt, S., & Rieder"),
        ("Huang2021",  "after",  "Huang, M., & Rust, R. (2020)"),
        ("Orlikowski", "before", "Patton, M. Q. (2014)"),
        ("Prasanna",   "before", "Radford, A., Narasimhan"),
        ("Vaid",       "before", "Vaswani, A., Shazeer"),
        ("Vargo",      "before", "Vaswani, A., Shazeer"),
        ("Wharton",    "before", "Woodside, A. G."),
    ]
    for key, where, marker in ref_plan:
        anchor_p = find_para(doc, marker)
        assert anchor_p is not None, f"reference anchor not found: {marker!r}"
        new_p = ref_para(REFS[key], used)
        (insert_before if where == "before" else insert_after)(anchor_p, new_p)
        results.append((f"6. ref {key} ({where} {marker[:22]}...)", True))

    # report ---------------------------------------------------------------- #
    print("\n".join(f"   [{'ok' if ok else 'FAIL'}] {label}" for label, ok in results))
    failed = [l for l, ok in results if not ok]
    assert not failed, f"\nFAILED operations: {failed}"

    doc.save(str(DOCX_PATH))
    print(f"\nSaved: {DOCX_PATH}\nBackup: {BACKUP}")


if __name__ == "__main__":
    main()
