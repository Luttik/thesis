# -*- coding: utf-8 -*-
"""
Two refinements to §5.1 (clean, non-tracked):
  A. Add a dedicated positioning subsection §5.1.2 "Extending research on AI in
     marketing" (parallel to §5.1.1's digital-transformation positioning), then
     renumber the stage walk Observing/Steering/Applying/Value outcomes to
     §5.1.3–§5.1.6.
  B. Re-anchor the §4.4.4 / Table 4 divergent-outcomes finding in Value outcomes
     as evidence of the manager's DRIVING and MEDIATING role — externally
     triggered (sensed, not invented), managerially mediated. Not "inside-out".
"""
from __future__ import annotations

import copy, shutil
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn

from patch_sec44_inside_out import find_elem, insert_before
from patch_sec51_discussion import clean_body, clean_heading

ROOT      = Path(__file__).resolve().parents[1]
DOCX_PATH = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP    = ROOT / "Thesis Draft - Daan Luttik - MBA.aimkt-backup.docx"

S512_AIMKT = [
    ("This contribution also speaks directly to research on AI in marketing. That "
     "literature has established that AI contributes across the marketing process rather "
     "than only within communications (Vaid et al., 2025; Prasanna & Kushwaha, 2025); that "
     "the value it creates is multidimensional and often internally conflicting, trading "
     "efficiency against governance, personalization against privacy, and throughput "
     "against distinctiveness (Brynjolfsson et al., 2025; Huang & Rust, 2021); and that "
     "this value is realized only when AI is aligned with strategy, knowledge, and "
     "decision-making rather than treated as an isolated technical project (Enholm et al., "
     "2022; Kitsios & Kamariotou, 2021; Prasad Agrawal, 2023). The field has, in other "
     "words, already argued that value creation with AI is a *situated managerial process* "
     "rather than a purely technical effect, and it has issued explicit calls for empirical "
     "work on agentic systems specifically, beyond the prevailing focus on content "
     "generation (Kim, 2025; Mogaji & Jain, 2024; Jain et al., 2024)."),
    ("This study advances that agenda in three ways. First, where prior work could assert "
     "the situated, managerial character of AI value largely in principle, the present "
     "findings give it empirical content: the process model specifies what that managerial "
     "process consists of, and renders the *translation work* the literature names (Enholm "
     "et al., 2022) as a concrete repertoire of observing, steering, and applying. Second, "
     "it shifts the analytical weight from the technology to the manager. Influential "
     "AI-in-marketing frameworks are organized around types of AI and their task "
     "capabilities (Huang & Rust, 2021), locating value in what the technology can do; this "
     "account locates it instead in the managerial work that drives and mediates value, "
     "treating the agentic system as a resource that managers configure rather than as the "
     "source of value itself. Third, it widens the conception of marketing value beyond the "
     "efficiency-and-content lens that dominates the generative-AI literature (Wahid et "
     "al., 2023; Grewal et al., 2025; Kumar et al., 2025) to a managed portfolio in which "
     "benefits, sacrifices, and risks are produced together and value destruction is "
     "actively governed. The result is one of the first grounded answers to the "
     "field’s call: an account in which marketing managers, prompted by an external "
     "environment they observe rather than by an opportunity they invent, drive and mediate "
     "the creation of value with agentic AI."),
]

# Table 4 / managerial-mediation paragraph (inserted into Value outcomes, after its P1)
MEDIATION = (
    "The clearest evidence that this value is managerially mediated rather than "
    "technologically determined is that comparable use cases produced divergent outcomes "
    "across organizations (Section 4.4.4; Table 4): the same analytics, content, or "
    "customer-facing use case proved transformative in one organization and stalled in "
    "another, and the difference lay in the managerial work and the configuration around "
    "it, not in the technology, which was largely shared. Crucially, this is a mediating "
    "role within an externally initiated process: managers do not generate the opportunity "
    "in isolation but sense it from the changing environment (Section 5.1.3) and then drive "
    "and mediate its translation into value. It is in this sense that the manager, rather "
    "than the agentic system, is the central actor in value creation."
)

RENUMBER = [
    ("Observing: sensing opportunity in a volatile context", "5.1.3"),
    ("Steering: the managerial repertoire",                   "5.1.4"),
    ("Applying: from workflow to harness",                    "5.1.5"),
    ("Value outcomes: a managed portfolio",                   "5.1.6"),
]


def set_heading_number(p, number):
    wts = p.findall(".//" + qn("w:t"))
    assert len(wts) == 2, f"heading has {len(wts)} w:t, expected 2"
    wts[0].text = number


def main():
    shutil.copy(DOCX_PATH, BACKUP)
    doc = Document(str(DOCX_PATH))

    h_obs = find_elem(doc, "Observing: sensing opportunity in a volatile context")
    assert h_obs is not None, "Observing heading not found"
    tmpl = copy.deepcopy(h_obs)  # Heading3 template

    # A1. build + insert new §5.1.2 before Observing
    new = [clean_heading(tmpl, "5.1.2", "Extending research on AI in marketing")]
    new += [clean_body(s) for s in S512_AIMKT]
    insert_before(h_obs, new)
    print("A1. inserted new §5.1.2 'Extending research on AI in marketing'")

    # A2. renumber the four stage headings
    for title, num in RENUMBER:
        h = find_elem(doc, title)
        assert h is not None, f"heading not found: {title}"
        set_heading_number(h, num)
    print("A2. renumbered stage subsections -> 5.1.3, 5.1.4, 5.1.5, 5.1.6")

    # B. insert the mediation/Table 4 paragraph into Value outcomes, after P1
    p2 = find_elem(doc, "The most distinctive finding at this stage concerns how the portfolio")
    assert p2 is not None, "Value-outcomes P2 not found"
    insert_before(p2, [clean_body(MEDIATION)])
    print("B. inserted Table 4 / managerial-mediation paragraph into §5.1.6")

    doc.save(str(DOCX_PATH))
    print(f"\nSaved: {DOCX_PATH}\nBackup: {BACKUP}")


if __name__ == "__main__":
    main()
