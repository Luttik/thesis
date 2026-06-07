# -*- coding: utf-8 -*-
"""
Rewrite §2.3 and §5.1.1, and add two Teece reference entries (all tracked, author "Claude").

1. §2.3  - replace the 5 existing paragraphs with 3 tightened, fully-sourced paragraphs
           focused on the concepts carried into §5.1: digital transformation as
           organizational change, dynamic capabilities (already applied to DT), and the
           digital paradox / complementary assets.
2. §5.1.1 - replace the 3 working-draft paragraphs with 3 paragraphs that (a) acknowledge
            where DC has already been applied to DT, (b) differentiate the contribution by
            following the chain past reconfiguration to value, and (c) bring both §2.3
            notes (complementary assets; DT-as-organizational-change) into the argument.
3. References - add Teece (1986) and Teece (2007), before the Teece/Pisano/Shuen (1997) entry.

Reuses the tracked-change helpers from patch_sec44_inside_out.py.
"""
from __future__ import annotations

import copy
import shutil
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from lxml import etree

from patch_sec44_inside_out import (
    _used_ids, _nid, full_text, find_elem, insert_before,
    AUTHOR, DATE, XMLSPACE,
)

ROOT      = Path(__file__).resolve().parents[1]
DOCX_PATH = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP    = ROOT / "Thesis Draft - Daan Luttik - MBA.sec23-backup.docx"

MD   = " — "      # spaced em dash
APOS = "’"   # ’
EN   = "–"   # – (page ranges)


# --------------------------------------------------------------------------- #
# builders (body paragraph in teal 00312A; reference entry with white highlight)
# --------------------------------------------------------------------------- #
def _stamp(el, used):
    el.set(qn("w:id"), str(_nid(used)))
    el.set(qn("w:author"), AUTHOR)
    el.set(qn("w:date"), DATE)


def _wrap_run_in_del(r_elem, used):
    """Return a <w:del> wrapping a copy of r_elem, with <w:t> -> <w:delText>."""
    d = etree.Element(qn("w:del")); _stamp(d, used)
    rc = copy.deepcopy(r_elem)
    for t in rc.findall(qn("w:t")):
        dt = etree.Element(qn("w:delText")); dt.set(XMLSPACE, "preserve"); dt.text = t.text or ""
        t.getparent().replace(t, dt)
    d.append(rc)
    return d


def del_para_deep(p_elem, used):
    """Mark a whole paragraph deleted, including runs nested in existing <w:ins>
    (insert-then-delete) and <w:hyperlink>, so nothing survives accept/reject."""
    pPr = p_elem.find(qn("w:pPr"))
    if pPr is None:
        pPr = etree.Element(qn("w:pPr")); p_elem.insert(0, pPr)
    rPr = pPr.find(qn("w:rPr"))
    if rPr is None:
        rPr = etree.SubElement(pPr, qn("w:rPr"))
    if rPr.find(qn("w:del")) is None:                      # paragraph-mark deletion
        dmark = etree.Element(qn("w:del")); _stamp(dmark, used); rPr.insert(0, dmark)
    for r in p_elem.findall(qn("w:r")):                    # direct runs
        p_elem.replace(r, _wrap_run_in_del(r, used))
    for ins in p_elem.findall(qn("w:ins")):                # prior unaccepted insertions
        for r in ins.findall(qn("w:r")):
            ins.replace(r, _wrap_run_in_del(r, used))
    for hl in p_elem.findall(qn("w:hyperlink")):           # runs inside hyperlinks
        for r in hl.findall(qn("w:r")):
            hl.replace(r, _wrap_run_in_del(r, used))


def ins_body_para(segments, used):
    """segments: list of (text, italic). Tracked-inserted body paragraph, color 00312A."""
    p = etree.Element(qn("w:p"))
    pPr = etree.SubElement(p, qn("w:pPr"))
    rPr = etree.SubElement(pPr, qn("w:rPr"))
    _stamp(etree.SubElement(rPr, qn("w:ins")), used)          # paragraph-mark inserted
    etree.SubElement(rPr, qn("w:color")).set(qn("w:val"), "00312A")
    ins = etree.SubElement(p, qn("w:ins")); _stamp(ins, used)
    for text, italic in segments:
        r = etree.SubElement(ins, qn("w:r"))
        rpr = etree.SubElement(r, qn("w:rPr"))
        if italic:
            etree.SubElement(rpr, qn("w:i")); etree.SubElement(rpr, qn("w:iCs"))
        etree.SubElement(rpr, qn("w:color")).set(qn("w:val"), "00312A")
        t = etree.SubElement(r, qn("w:t")); t.set(XMLSPACE, "preserve"); t.text = text
    return p


def ins_ref_para(segments, used):
    """segments: list of (text, italic). Reference entry: hanging indent + white highlight."""
    p = etree.Element(qn("w:p"))
    pPr = etree.SubElement(p, qn("w:pPr"))
    ind = etree.SubElement(pPr, qn("w:ind")); ind.set(qn("w:left"), "720"); ind.set(qn("w:hanging"), "720")
    rPr = etree.SubElement(pPr, qn("w:rPr"))
    _stamp(etree.SubElement(rPr, qn("w:ins")), used)
    etree.SubElement(rPr, qn("w:highlight")).set(qn("w:val"), "white")
    ins = etree.SubElement(p, qn("w:ins")); _stamp(ins, used)
    for text, italic in segments:
        r = etree.SubElement(ins, qn("w:r"))
        rpr = etree.SubElement(r, qn("w:rPr"))
        if italic:
            etree.SubElement(rpr, qn("w:i")); etree.SubElement(rpr, qn("w:iCs"))
        etree.SubElement(rpr, qn("w:highlight")).set(qn("w:val"), "white")
        t = etree.SubElement(r, qn("w:t")); t.set(XMLSPACE, "preserve"); t.text = text
    return p


# --------------------------------------------------------------------------- #
# content
# --------------------------------------------------------------------------- #
SEC23 = [
    # P1 — DT as organizational change (the note Daan liked), now sourced
    [
        ("The literature on digital transformation provides the central bridge between "
         "technological capability and managerial value creation. Its core lesson is that "
         "digital transformation is not simply the adoption of digital tools; it involves "
         "changes in organizational processes, business models, capabilities, and sometimes "
         "organizational identity (Hanelt et al., 2021; Verhoef et al., 2021; Wessel et al., "
         "2021). Verhoef et al. (2021) separate ", False),
        ("digitization", True),
        (" (converting analog information into digital form) and ", False),
        ("digitalization", True),
        (" (using digital tools to improve existing processes) from ", False),
        ("digital transformation", True),
        (", which alters business models and organizational logic; Wessel et al. (2021) add "
         "that digital transformation builds a new organizational identity rather than merely "
         "reinforcing the existing one. For agentic AI the distinction is decisive: used only "
         "to draft emails or summarize documents it remains a digitalization tool, but where "
         "it reshapes how marketing teams sense opportunities, allocate work, and serve "
         "customers it becomes part of a transformation. Holmström (2022) frames AI "
         "readiness as the bridge between AI experimentation and that transformation, since "
         "organizations must first develop the capabilities, data, governance, and learning "
         "practices that let AI be used productively. This thesis therefore treats agentic AI "
         "adoption as a managerial and organizational phenomenon rather than a software "
         "implementation.", False),
    ],
    # P2 — dynamic capabilities, and that DC has ALREADY been applied to DT
    [
        ("Dynamic capabilities theory gives this organizational view its sharpest tools. "
         "Teece et al. (1997) define dynamic capabilities as a firm" + APOS + "s ability to "
         "integrate, build, and reconfigure internal and external competences in response to a "
         "changing environment, and Teece (2007) disaggregates them into the microfoundations "
         "of ", False),
        ("sensing", True),
        (" opportunities, ", False),
        ("seizing", True),
        (" them, and ", False),
        ("transforming", True),
        (" (reconfiguring) the resource base. This framework has already been carried into the "
         "digital-transformation sphere: Warner and Wäger (2019) show that incumbents "
         "build digital transformation through ongoing strategic renewal of business models, "
         "collaboration, and culture; Ellström et al. (2021) identify digital sensing, "
         "digital strategy, and the creation of unified digital infrastructure as the seizing "
         "and reconfiguring routines of transformation; and Hanelt et al. (2021) describe the "
         "more malleable organizational designs that continuous digital adaptation demands. "
         "These accounts establish dynamic capabilities as a productive lens for technological "
         "change, but they remain largely at the firm and strategy level and concentrate on "
         "how renewal capabilities are built" + MD + "a point Section 5.1 returns to and "
         "extends.", False),
    ],
    # P3 — the digital paradox / complementary assets (the note Daan liked), now sourced
    [
        ("A final lesson tempers any purely technological account of success. Organizations "
         "often fail to extract value from digital technologies despite heavy investment" + MD +
         "a pattern described as the ", False),
        ("digital paradox", True),
        (" (Ancillai et al., 2023; Enholm et al., 2022)" + MD + "because technology value is "
         "mediated by complementary assets: the skills, data, organizational structure, "
         "leadership, culture, and process redesign that surround the tool (Teece, 1986). For "
         "agentic AI this means a technically capable agent will not create marketing value on "
         "its own; it must be embedded in a work system in which people know when to delegate, "
         "when to intervene, how to measure performance, and how to hold the system "
         "accountable. This proposition" + MD + "that value is produced by the configuration "
         "around the technology rather than the technology itself" + MD + "is the central "
         "thread the empirical study develops, and Section 5.1 returns to it directly.", False),
    ],
]

SEC511 = [
    # P1 — mapping, acknowledge DC-already-in-DT, and the move past reconfiguration to value
    [
        ("The model in Figure 1 maps closely onto dynamic capabilities theory (Teece et al., "
         "1997; Teece, 2007), and rendering that theory in the agentic-AI-in-marketing setting "
         "through a grounded account is in itself part of the contribution. ", False),
        ("Observing", True),
        (" corresponds to digital sensing (Ellström et al., 2021; Warner & Wäger, "
         "2019); ", False),
        ("steering", True),
        (MD + "reshaping, leveraging, and navigating organizational conditions" + MD +
         "performs the seizing and transforming work through which a firm renews its resource "
         "base; and ", False),
        ("applying", True),
        (" is the deployment of that renewed base in use. Dynamic capabilities have already "
         "been carried into the digital-transformation sphere by this same literature, but it "
         "concentrates on how firms build sensing and renewal capabilities and tends to stop "
         "at the reconfigured resource base. The present study follows the chain one step "
         "further" + MD + "to the value that the reconfigured state actually creates" + MD +
         "and it is there, rather than in the act of reconfiguration, that its distinctive "
         "findings lie.", False),
    ],
    # P2 — relocating the binding constraint + complementary assets / digital paradox
    [
        ("The first concerns where the binding constraint sits, and it is not where the "
         "dynamic-capabilities emphasis on sensing would predict. Sensing was not the scarce "
         "capability: participants across roles and organizations observed the same "
         "hockey-stick progression (Section 4.1.1), the same competitive and consumer-driven "
         "market pressure (Section 4.1.2), and the same vendor roadmaps (Section 4.1.3). What "
         "separated organizations was the follow-through" + MD + "building literacy, freeing "
         "data, providing clarity, and protecting experimentation, and then orchestrating "
         "these into a working configuration; the divergent outcomes for comparable use cases "
         "make the difference visible (Section 4.4.4; Table 4). This relocates the locus of "
         "differentiation from opportunity recognition to organizational follow-through, and "
         "it gives empirical specificity to the long-standing argument that the value of a "
         "digital technology is mediated by complementary assets rather than realized "
         "automatically (Ancillai et al., 2023; Enholm et al., 2022; Holmström, 2022; "
         "Teece, 1986). The ", False),
        ("digital paradox", True),
        (" of earlier technological waves recurs here: a technically capable agent creates no "
         "marketing value on its own, and the complementary assets that convert it into value "
         "are precisely the configurational elements this study identifies" + MD + "the "
         "harness, the organizational conditions, and the managerial behaviors around the "
         "agent.", False),
    ],
    # P3 — DT-as-organizational-change applied at the use-case level + asset orchestration
    [
        ("The second reframes what that follow-through is. Digital transformation has long "
         "been understood as more than the adoption of tools" + MD + "as change in "
         "organizational processes, business models, capabilities, and sometimes identity "
         "(Hanelt et al., 2021; Verhoef et al., 2021; Wessel et al., 2021)" + MD + "and the "
         "present findings show the same holds at the level of an individual agentic use case: "
         "value is produced by the organizational configuration in which the technology is "
         "embedded, not by the technology itself. Dynamic capabilities theory anticipates this "
         "step in the abstract, through Teece" + APOS + "s (2007) notion of ", False),
        ("asset orchestration", True),
        (MD + "the managerial coordination of co-specialized resources" + MD + "but leaves it "
         "empirically thin. By specifying what that orchestration consists of in the "
         "agentic-AI setting, the study gives concrete, microfoundational content to a step "
         "the framework names but rarely opens up. How that configuration co-produces value "
         "in use is developed in Section 5.1.2; whether configuration-based advantages can be "
         "", False),
        ("captured", True),
        (" and sustained rather than merely ", False),
        ("created", True),
        (" (Lepak et al., 2007) is a question the framework raises and this study" + APOS +
         "s design leaves open.", False),
    ],
]

REF_TEECE_1986 = [
    ("Teece, D. J. (1986). Profiting from technological innovation: Implications for "
     "integration, collaboration, licensing and public policy. ", False),
    ("Research Policy, 15", True),
    ("(6), 285" + EN + "305. https://doi.org/10.1016/0048-7333(86)90027-2", False),
]
REF_TEECE_2007 = [
    ("Teece, D. J. (2007). Explicating dynamic capabilities: The nature and microfoundations "
     "of (sustainable) enterprise performance. ", False),
    ("Strategic Management Journal, 28", True),
    ("(13), 1319" + EN + "1350. https://doi.org/10.1002/smj.640", False),
]


# --------------------------------------------------------------------------- #
def main():
    shutil.copy(DOCX_PATH, BACKUP)
    doc  = Document(str(DOCX_PATH))
    used = _used_ids(doc)

    # resolve anchors (element refs survive insertions) -------------------- #
    a23 = [
        find_elem(doc, "important bridge between AI capability"),
        find_elem(doc, "If agentic AI is used only to draft emails"),
        find_elem(doc, "Dynamic capabilities theory is particularly useful in this context"),
        find_elem(doc, "These insights suggest three lessons"),
        find_elem(doc, "The digital transformation literature also warns"),
    ]
    a511 = [
        find_elem(doc, "Clear links can be made between the model from Figure 1"),
        find_elem(doc, "First, we go beyond reconfiguration"),
        find_elem(doc, "The study" + APOS + "s distinctive contribution, however, is to show where the binding constraint"),
    ]
    p_ref_teece = find_elem(doc, "Dynamic capabilities and strategic management. Strategic Management Journal")

    for i, el in enumerate(a23):
        assert el is not None, f"§2.3 anchor {i} not found"
    for i, el in enumerate(a511):
        assert el is not None, f"§5.1.1 anchor {i} not found"
    assert p_ref_teece is not None, "Teece (1997) reference anchor not found"

    # 1. §2.3 rewrite ------------------------------------------------------ #
    insert_before(a23[0], [ins_body_para(segs, used) for segs in SEC23])
    for el in a23:
        del_para_deep(el, used)
    print(f"1. §2.3: inserted {len(SEC23)} new paragraphs; deleted {len(a23)} old paragraphs")

    # 2. §5.1.1 rewrite ---------------------------------------------------- #
    insert_before(a511[0], [ins_body_para(segs, used) for segs in SEC511])
    for el in a511:
        del_para_deep(el, used)
    print(f"2. §5.1.1: inserted {len(SEC511)} new paragraphs; deleted {len(a511)} old paragraphs")

    # 3. references: Teece (1986) and Teece (2007) before Teece et al. (1997)
    insert_before(p_ref_teece, [ins_ref_para(REF_TEECE_1986, used),
                                 ins_ref_para(REF_TEECE_2007, used)])
    print("3. references: added Teece (1986) and Teece (2007)")

    doc.save(str(DOCX_PATH))
    print(f"\nSaved: {DOCX_PATH}\nBackup: {BACKUP}")


if __name__ == "__main__":
    main()
