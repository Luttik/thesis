# -*- coding: utf-8 -*-
"""
Rewrite the Discussion §5.1.2–§5.1.5 around the process model, manager-central.

- KEEP §5.1 intro and §5.1.1 (digital-transformation continuity + conditions).
- TRACKED fix to the intro's residual "inside-out" sentence (para after 5.1.1 mapping).
- CLEAN (non-tracked) replacement of the old §5.1.2/§5.1.3/§5.1.4 with four new
  stage subsections: Observing, Steering, Applying, Value outcomes.
- Remove comment 137 (Daan's @claude note, now addressed by the rewrite).

Reuses tracked-change + element helpers from the existing patch scripts.
Body paragraphs use NO explicit run color (matches the document default / §5.1.1).
"""
from __future__ import annotations

import copy
import shutil
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from lxml import etree

from patch_sec44_inside_out import (
    _used_ids, find_elem, insert_before, AUTHOR, DATE, XMLSPACE,
)
from patch_sec23_dc_value import del_para_deep, _stamp

ROOT      = Path(__file__).resolve().parents[1]
DOCX_PATH = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP    = ROOT / "Thesis Draft - Daan Luttik - MBA.sec51-backup.docx"


# --------------------------------------------------------------------------- #
# inline italic markup:  "...*term*..."  ->  [(text, italic), ...]
# --------------------------------------------------------------------------- #
def segs(s: str):
    out, italic = [], False
    for chunk in s.split("*"):
        if chunk:
            out.append((chunk, italic))
        italic = not italic
    return out


def clean_body(s: str):
    """Clean (non-tracked) body paragraph, no explicit color (inherits Normal)."""
    p = etree.Element(qn("w:p"))
    for text, italic in segs(s):
        r = etree.SubElement(p, qn("w:r"))
        if italic:
            rpr = etree.SubElement(r, qn("w:rPr"))
            etree.SubElement(rpr, qn("w:i"))
            etree.SubElement(rpr, qn("w:iCs"))
        t = etree.SubElement(r, qn("w:t")); t.set(XMLSPACE, "preserve"); t.text = text
    return p


def clean_heading(template_p, number: str, title: str):
    """Clone a Heading3 template paragraph; set its number + title runs."""
    p = copy.deepcopy(template_p)
    wts = p.findall(".//" + qn("w:t"))
    assert len(wts) == 2, f"expected 2 w:t in heading template, got {len(wts)}"
    wts[0].text = number
    wts[1].text = title
    return p


def ins_body_nocolor(s: str, used):
    """Tracked-inserted body paragraph, no explicit color."""
    p = etree.Element(qn("w:p"))
    pPr = etree.SubElement(p, qn("w:pPr"))
    rPr = etree.SubElement(pPr, qn("w:rPr"))
    _stamp(etree.SubElement(rPr, qn("w:ins")), used)          # paragraph mark inserted
    ins = etree.SubElement(p, qn("w:ins")); _stamp(ins, used)
    for text, italic in segs(s):
        r = etree.SubElement(ins, qn("w:r"))
        if italic:
            rpr = etree.SubElement(r, qn("w:rPr"))
            etree.SubElement(rpr, qn("w:i")); etree.SubElement(rpr, qn("w:iCs"))
        t = etree.SubElement(r, qn("w:t")); t.set(XMLSPACE, "preserve"); t.text = text
    return p


def remove_comment(doc, cid: str):
    """Strip comment <cid>: range markers/reference in document.xml + entry in comments.xml."""
    bodyroot = doc.part._element
    removed = 0
    for tag in ("commentRangeStart", "commentRangeEnd", "commentReference"):
        for el in bodyroot.iter(qn("w:" + tag)):
            if el.get(qn("w:id")) == cid:
                parent = el.getparent()
                # if reference sits alone in a run, drop the run too
                gp = parent.getparent()
                if parent.tag == qn("w:r") and len(parent) <= 2:
                    gp.remove(parent)
                else:
                    parent.remove(el)
                removed += 1
    # comments.xml
    for rel in doc.part.rels.values():
        if rel.reltype.endswith("/comments"):
            croot = rel.target_part._element
            for c in list(croot):
                if c.get(qn("w:id")) == cid:
                    croot.remove(c)
    return removed


# --------------------------------------------------------------------------- #
# content
# --------------------------------------------------------------------------- #
INTRO_FIX = (
    "Running through the chain is a set of paradoxes, in which the technology that "
    "generates a problem also supplies the means to manage it. The model is offered as an "
    "interpretive account of how value is constructed: it makes visible the managerial "
    "work — observing, building conditions, steering, applying, and managing outcomes "
    "— through which agentic AI is turned into value, and that work is the subject of "
    "the sections that follow."
)

S512 = [
    (   # Observing P1
        "The model’s first stage locates value creation before any technology is "
        "deployed, in how managers observe a fast-moving environment. Across the data, "
        "managers attended to three external signals: the rapid progression of AI "
        "capability (Section 4.1.1), market pressure from competitors and, increasingly, "
        "from consumers acting through their own agents (Section 4.1.2), and the roadmaps "
        "communicated by their software suppliers (Section 4.1.3). Reading these signals "
        "corresponds closely to what the dynamic-capabilities literature calls *sensing* "
        "— the identification of opportunities and threats in a changing environment "
        "(Teece, 1997, 2007) — and, in the digital setting, to the digital sensing "
        "routines through which firms detect technological change (Ellström et al., "
        "2021). In answering the calls for research into agentic AI in marketing (Kim, "
        "2025; Mogaji & Jain, 2024), the study’s first observation is that managers "
        "are, on the whole, competent sensors: the arrival and relevance of agentic AI was "
        "widely and similarly perceived."
    ),
    (   # Observing P2
        "The contribution lies in what this reveals about where managerial differentiation "
        "begins. Because sensing was broadly shared, it was not the scarce capability; what "
        "distinguished managers was a more skeptical, evaluative form of observation. "
        "Participants who created value treated reported use cases as claims to be tested "
        "rather than facts to be adopted, distinguishing what is operationally running from "
        "what is merely announced — the *optics-versus-reality* discipline visible "
        "throughout the data (Section 4.3.1), and a necessary response to a category that "
        "one participant judged to have “become almost a marketing term” (Section "
        "4.1.2). Observing, in this setting, is thus not only the perception of opportunity "
        "but the disciplined separation of genuine capability from hype, and it is the "
        "first point at which the manager’s judgment, rather than the technology, "
        "begins to shape the value that will follow."
    ),
]

S513 = [
    (   # Steering P1
        "If observing identifies the opportunity, steering is where value is won or lost. "
        "Section 5.1.1 established that the organizational conditions surrounding agentic AI "
        "— literacy, data and infrastructure, leadership, and governance — matter "
        "even more than in earlier waves of digital transformation; the present "
        "contribution concerns how managers act on those conditions. The study identifies a "
        "three-part repertoire: managers *reshape* conditions they control, *leverage* "
        "conditions that are already favorable, and *navigate* conditions they cannot "
        "change by working within them. This gives microfoundational, marketing-specific "
        "content to the *seizing* and *reconfiguring* activities that dynamic-capabilities "
        "theory names but tends to treat at the level of the firm (Teece, 1997, 2007; "
        "Ellström et al., 2021; Hanelt et al., 2021)."
    ),
    (   # Steering P2
        "Two features of how the repertoire is used are analytically central. The first is "
        "a systematic *navigation bias*: managers reshaped conditions internal to their own "
        "teams — educating differentially by level, running experiments, bringing "
        "people along, providing clarity, and championing the work — but defaulted to "
        "navigating conditions that originated elsewhere in the organization, most clearly "
        "the restrictive governance documented in Section 5.1.1 and the scarce technical "
        "resources of Section 4.2.3; no instance of reshaping the governance regime itself "
        "was observed. This marks a boundary to managerial agency that the firm-level "
        "literature underplays, and it resonates with work on resistance to change and AI "
        "readiness (Cieslak & Valor, 2025; Li et al., 2023) and the organizational-"
        "capability view of AI adoption (Romeo & Lacko, 2026; Weber et al., 2023). The "
        "second is the disproportionate role of the AI champion — an actor combining "
        "technical and business fluency who converts leadership backing into organization-"
        "wide change (Section 4.2.2), and who is largely absent from the firm-level account."
    ),
    (   # Steering P3 (addresses comment 137 + implementation paradox)
        "This stage is also where the study departs most sharply from any account that "
        "locates value in the technology, or even its configuration, alone. Value did not "
        "follow from procuring or configuring a capable system; it followed from managerial "
        "work that is easy to underestimate. A well-built system that no one is brought "
        "along to use creates no value, and an initiative that never starts — because "
        "it remains caught in legal or procurement review — forgoes value entirely. "
        "This is the substance of the implementation paradox (Section 4.5.3): agentic tools "
        "are unusually easy to begin with, yet operationalizing them at organizational "
        "scale is slow and effortful, a mismatch one participant captured as technology "
        "that changes exponentially meeting organizations that change logarithmically. The "
        "managerial task that steering names is precisely the closing of that gap — "
        "protecting and funding experimentation so that initiatives actually start, and "
        "then doing the unglamorous work of embedding a proven prototype into routine "
        "practice."
    ),
]

S514 = [
    (   # Applying P1
        "Steering creates the conditions; applying is the act of putting agentic AI to "
        "work, and the data show it to be a deliberate design task rather than a purchase. "
        "Value was most reliably created when managers began from a marketing problem or "
        "workflow rather than from the technology, decomposed that workflow into steps, and "
        "inserted agentic AI only where they trusted its performance, retaining human "
        "judgment elsewhere (Section 4.3.1). Where the agent was then deployed, what most "
        "shaped the result was its *harness* — the data it can reach, its memory, the "
        "tools it can call, its instructions, and its guardrails — together with the "
        "surrounding data infrastructure and integration with existing systems (Section "
        "4.3.2). Designing this harness deliberately is itself a managerial intervention, "
        "and one that the study’s most technically experienced participants treated as "
        "the real object of design."
    ),
    (   # Applying P2 (config is one component, not sole determinant -> answers comment 137)
        "Theoretically, this stage gives empirical specificity to the practice-lens claim "
        "that a technology’s effects are emergent in its use rather than fixed in the "
        "artifact (Orlikowski, 2000), and it aligns the findings with value co-creation "
        "accounts in which technology actively participates in resource integration rather "
        "than serving as a passive instrument (Vargo & Lusch, 2017; Kaartemo & Helkkula, "
        "2018; Leone et al., 2021). The study’s addition is to specify the "
        "configurational elements — the harness and its technical surround — "
        "through which an agentic system becomes a value-creating actor. This configuration "
        "is one component of value creation rather than its sole determinant: as the "
        "preceding stage made clear, the most carefully engineered harness yields nothing "
        "if the organization is not steered to adopt it. Applying and steering are "
        "complementary managerial acts, and value emerges from their combination."
    ),
]

S515 = [
    (   # Value outcomes P1 (value lens)
        "The model’s final stage concerns the value that results, and the "
        "study’s contribution here is to show that this value is not a single quantity "
        "but a portfolio that managers must actively compose. Participants described "
        "benefits (efficiency, scale, extension of skill, and quality), sacrifices (cost "
        "and the displacement or reshaping of roles), and risks (hallucination, security "
        "and privacy violation, and brand degradation) as produced together rather than "
        "traded one for another (Section 4.4). Read through value theory, these outcomes "
        "span the operational, customer, and strategic levels distinguished in Section 2.4, "
        "and they expose a distinction that efficiency-centred accounts of AI obscure: "
        "value *created* for the customer is not the same as value *captured* by the firm, "
        "and an organization can capture cost savings while destroying customer value "
        "through lost trust or authenticity. The manager’s task at this stage is "
        "therefore one of choice and measurement — deciding which value to pursue and "
        "benchmarking AI output against a human baseline so that improvement, rather than "
        "mere novelty, can be demonstrated."
    ),
    (   # Value outcomes P2 (elevated AI-governs-AI mechanism)
        "The most distinctive finding at this stage concerns how the portfolio’s "
        "negative terms are contained. Rather than treating value destruction (Doshi & "
        "Hauser, 2024) as a side effect to be avoided, managers managed it recursively, "
        "deploying agentic AI to govern the very risks that agentic AI creates: brand-"
        "control and tone-of-voice agents police brand risk (Section 4.5.1), while "
        "evaluator agents and human sense-checking limit the impact of hallucination "
        "(Section 4.5.2). Because human work carries its own error and bias, the operative "
        "standard is *comparative* rather than absolute — the question is not whether "
        "the agent errs but whether it errs less than the process it replaces. This "
        "reframes value destruction in the AI context as a condition that is actively and "
        "increasingly self-governed, and it carries a corollary: the organizations most "
        "exposed to AI-driven value destruction also have the strongest incentive, and the "
        "readiest means, to invest in AI-driven control."
    ),
    (   # Value outcomes P3 (junior paradox -> strategic value, bridge to 5.3)
        "One outcome, however, resists this containment and points beyond the firm. "
        "Deploying agentic AI first on junior tasks threatens the pipeline through which "
        "juniors become seniors (Section 4.5.4), trading a near-term operational gain for a "
        "longer-term erosion of capability that no efficiency metric records. This tension "
        "between operational and strategic value, like the emergence of consumers’ own "
        "agents as a new intermediary, is not resolved within the present data and is taken "
        "up again as a direction for future research in Section 5.3."
    ),
]


# --------------------------------------------------------------------------- #
def main():
    shutil.copy(DOCX_PATH, BACKUP)
    doc  = Document(str(DOCX_PATH))
    used = _used_ids(doc)

    # anchors --------------------------------------------------------------- #
    p_intro   = find_elem(doc, "its contribution lies primairily in locating the determinants")
    h_512     = find_elem(doc, "Value as configuration-in-use rather than capability")
    b_512     = find_elem(doc, "A second contribution concerns where value resides")
    h_513     = find_elem(doc, "A managerial repertoire and its navigation bias")
    b_513     = find_elem(doc, "Third, the study identifies a three-part repertoire")
    h_514     = find_elem(doc, "Value as an entangled portfolio, managed through paradox")
    b_514     = find_elem(doc, "Fourth, the findings recast the relationship between value")
    h_52      = find_elem(doc, "Practical implications")

    for nm, el in [("intro", p_intro), ("h512", h_512), ("b512", b_512),
                   ("h513", h_513), ("b513", b_513), ("h514", h_514),
                   ("b514", b_514), ("h52", h_52)]:
        assert el is not None, f"anchor not found: {nm}"

    tmpl_h3 = copy.deepcopy(h_512)   # Heading3 template (before deletion)

    # 1. tracked fix to the intro's inside-out sentence --------------------- #
    insert_before(p_intro, [ins_body_nocolor(INTRO_FIX, used)])
    del_para_deep(p_intro, used)
    print("1. intro: tracked replacement of the inside-out sentence")

    # 2. build + insert the four new stage subsections before §5.2 ---------- #
    new_elems = []
    new_elems.append(clean_heading(tmpl_h3, "5.1.2", "Observing: sensing opportunity in a volatile context"))
    new_elems += [clean_body(s) for s in S512]
    new_elems.append(clean_heading(tmpl_h3, "5.1.3", "Steering: the managerial repertoire"))
    new_elems += [clean_body(s) for s in S513]
    new_elems.append(clean_heading(tmpl_h3, "5.1.4", "Applying: from workflow to harness"))
    new_elems += [clean_body(s) for s in S514]
    new_elems.append(clean_heading(tmpl_h3, "5.1.5", "Value outcomes: a managed portfolio"))
    new_elems += [clean_body(s) for s in S515]
    insert_before(h_52, new_elems)
    print(f"2. inserted {len(new_elems)} new elements (4 headings + bodies) before §5.2")

    # 3. remove comment 137 (now addressed) before deleting its host para --- #
    n = remove_comment(doc, "137")
    print(f"3. removed comment 137 markers: {n}")

    # 4. clean-delete the old §5.1.2/§5.1.3/§5.1.4 (headings + bodies) ------- #
    for el in (h_512, b_512, h_513, b_513, h_514, b_514):
        el.getparent().remove(el)
    print("4. removed old §5.1.2/§5.1.3/§5.1.4 (6 paragraphs)")

    doc.save(str(DOCX_PATH))
    print(f"\nSaved: {DOCX_PATH}\nBackup: {BACKUP}")


if __name__ == "__main__":
    main()
