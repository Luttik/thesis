# -*- coding: utf-8 -*-
"""
Refocus §2.4 and §5.1.1 on the digital-transformation ↔ agentic-AI link (tracked, author "Claude").

1. §2.4   - replace the 4 paragraphs with 2: (a) what the DT literature teaches, with the
            DT papers explained and the digital paradox / complementary assets; (b) treat agentic
            AI as the latest DT wave and position the study. Dynamic capabilities reduced to one
            light mention.
2. §5.1.1 - replace the 3 paragraphs with 2: (a) the study as a *continuation* of DT (central
            finding confirms it; preserves the user's Bughin/Vidal/Wharton citations); (b) the
            agentic-specific tunings, each grounded in a Chapter-4 section. Drops the
            observing/sensing mapping and "asset orchestration".
3. §5.1.1 heading renamed to "Agentic AI value creation as a continuation of digital transformation".
4. References - remove the now-unused Teece (2007) entry.
5. TOC - swap the 2.3 / 2.4 titles to match the body after the section swap.

Reuses helpers from patch_sec44_inside_out.py and patch_sec23_dc_value.py.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from patch_sec44_inside_out import (
    _used_ids, full_text, find_elem, insert_before, replace_text_tracked, AUTHOR,
)
from patch_sec23_dc_value import ins_body_para, del_para_deep

ROOT      = Path(__file__).resolve().parents[1]
DOCX_PATH = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP    = ROOT / "Thesis Draft - Daan Luttik - MBA.refocus-backup.docx"

MD = " — "

SEC24 = [
    [
        ("The literature on digital transformation offers the closest precedent for what adopting "
         "agentic AI asks of an organization. It distinguishes transformation from the mere "
         "adoption of tools: Verhoef et al. (2021) separate ", False),
        ("digitization", True),
        (" (making information digital) and ", False),
        ("digitalization", True),
        (" (improving existing processes with digital tools) from ", False),
        ("digital transformation", True),
        (", which changes business models and organizational logic; Wessel et al. (2021) show it "
         "builds a new organizational identity rather than reinforcing the existing one; and "
         "Hanelt et al. (2021) document the continuous organizational change and more malleable "
         "structures it demands. A consistent lesson is the ", False),
        ("digital paradox", True),
        (": organizations frequently fail to extract value from digital technologies despite heavy "
         "investment (Ancillai et al., 2023; Enholm et al., 2022), because technology value is "
         "mediated by complementary assets" + MD + "the skills, data, processes, structure, and "
         "leadership that surround the tool (Teece, 1986). Holmström (2022) frames AI readiness as "
         "exactly this precondition: the capabilities, data, governance, and learning practices an "
         "organization must build before AI produces value.", False),
    ],
    [
        ("This thesis treats agentic AI as the latest wave of digital transformation and asks how "
         "its lessons apply. The expectation the literature sets is clear: a technically capable "
         "agent will not create marketing value on its own; it must be embedded in a work system "
         "that knows when to delegate, when to intervene, and how to remain accountable. Where "
         "earlier scholarship carried this thinking forward" + MD + "including work framing "
         "transformation as the building of dynamic capabilities (Teece et al., 1997) for ongoing "
         "renewal (Ellström et al., 2021; Warner & Wäger, 2019)" + MD + "it did so for prior "
         "technologies; the contribution of this study is to examine, empirically and in the "
         "marketing setting, how the digital-transformation account holds for agentic AI and where "
         "it must be tuned. Chapter 5 returns to this.", False),
    ],
]

SEC511 = [
    [
        ("The central finding of this study" + MD + "that value creation with agentic AI depends "
         "on internal conditions, managerial behavior, and the configuration in which the "
         "technology is applied rather than on the technology itself (Section 4.4.4)" + MD +
         "places the work within the digital-transformation tradition rather than apart from it. "
         "The ", False),
        ("digital paradox", True),
        (" of earlier waves recurs almost exactly: comparable use cases produced divergent "
         "outcomes (Table 4), and what separated success from failure was the complementary assets "
         "around the technology" + MD + "data infrastructure and connectivity for analytics, "
         "validation and brand-governance pipelines for content, and a proven baseline with "
         "leadership backing for customer-facing agents. Recent large-sample studies of AI "
         "adoption reinforce the same pattern: AI architecture is necessary but not sufficient, "
         "with organizational readiness" + MD + "people and processes" + MD + "rather than "
         "technical capacity forming the binding constraint on value (Bughin, 2024; Vidal et al., "
         "2022; Wharton Human-AI Research & GBK Collective, 2025). The study therefore reads less "
         "as a break with digital-transformation theory than as its continuation into a new "
         "technological wave, confirming that the value of a digital technology is realized through "
         "organizational follow-through rather than acquired with the tool (Ancillai et al., 2023; "
         "Enholm et al., 2022; Holmström, 2022; Teece, 1986).", False),
    ],
    [
        ("What the agentic setting adds is specificity about where that follow-through now lives, "
         "and the rest of this chapter develops it. The complementary assets that mediate value "
         "take a particular form" + MD + "the harness around the model and the organizational "
         "conditions surrounding it (Section 5.1.2). Efficiency, the most common benefit, was "
         "described as real but non-differentiating, expected to be competed away as every firm "
         "gains it (Section 4.4.1), so durable value depends on the configuration rather than on "
         "adoption itself (cf. Lepak et al., 2007, on the gap between creating and capturing "
         "value). And risk is managed recursively, the same technology deployed to govern its own "
         "failures (Section 5.1.4). These are extensions of digital-transformation thinking tuned "
         "to agentic AI, not departures from it.", False),
    ],
]

OLD_HEAD = "Extending dynamic capabilities to agentic AI in marketing"
NEW_HEAD = "Agentic AI value creation as a continuation of digital transformation"
T_LEARN  = "Learnings from earlier waves of digital transformation"
T_VALUE  = "Value theory and value creation with agentic AI"


def main():
    shutil.copy(DOCX_PATH, BACKUP)
    doc  = Document(str(DOCX_PATH))
    used = _used_ids(doc)

    # resolve all anchors first ------------------------------------------- #
    a24 = [
        find_elem(doc, "provides the central bridge between technological capability"),
        find_elem(doc, "For agentic AI the distinction is decisive"),
        find_elem(doc, "Dynamic capabilities theory gives this organizational view"),
        find_elem(doc, "A final lesson tempers any purely technological"),
    ]
    a511 = [
        find_elem(doc, "The model in Figure 1 maps closely onto dynamic capabilities"),
        find_elem(doc, "The first concerns where the binding constraint sits"),
        find_elem(doc, "The second reframes what that follow-through is"),
    ]
    p_head   = find_elem(doc, OLD_HEAD)
    p_ref07  = find_elem(doc, "Explicating dynamic capabilities: The nature and microfoundations")

    for i, el in enumerate(a24):  assert el is not None, f"§2.4 anchor {i} missing"
    for i, el in enumerate(a511): assert el is not None, f"§5.1.1 anchor {i} missing"
    assert p_head  is not None, "§5.1.1 heading missing"
    assert p_ref07 is not None, "Teece (2007) reference missing"

    # 1. §2.4 rewrite ----------------------------------------------------- #
    insert_before(a24[0], [ins_body_para(s, used) for s in SEC24])
    for el in a24:
        del_para_deep(el, used)
    print(f"1. §2.4: +{len(SEC24)} paragraphs / -{len(a24)} old")

    # 2. §5.1.1 rewrite --------------------------------------------------- #
    insert_before(a511[0], [ins_body_para(s, used) for s in SEC511])
    for el in a511:
        del_para_deep(el, used)
    print(f"2. §5.1.1: +{len(SEC511)} paragraphs / -{len(a511)} old")

    # 3. rename §5.1.1 heading ------------------------------------------- #
    ok = replace_text_tracked(p_head, OLD_HEAD, NEW_HEAD, used)
    print(f"3. heading rename: {'ok' if ok else 'FAILED'}")

    # 4. remove Teece (2007) reference ----------------------------------- #
    del_para_deep(p_ref07, used)
    print("4. reference Teece (2007) removed")

    # 5. TOC left as-is (static SDT; user does not need it corrected now).

    doc.save(str(DOCX_PATH))
    print(f"\nSaved: {DOCX_PATH}\nBackup: {BACKUP}")


if __name__ == "__main__":
    main()
