# -*- coding: utf-8 -*-
"""C2: consolidate §5.2 from eight recommendations to six (tracked, author 'Claude').
Keep the intro (add an Appendix B pointer); insert six new Heading3 + body paragraphs after it;
tracked-delete the eight old subsections."""
from __future__ import annotations
import copy, shutil
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP = ROOT / "Thesis Draft - Daan Luttik - MBA.sec52-backup.docx"
AUTHOR = "Claude"; DATE = "2026-06-07T20:00:00Z"
XS = "{http://www.w3.org/XML/1998/namespace}space"
A = "’"  # apostrophe

def used_ids(doc):
    return {int(el.get(qn("w:id"), 0)) for el in doc.element.body.iter() if el.get(qn("w:id")) is not None}
def nid(u): n = max(u, default=0) + 1; u.add(n); return n
def atext(el): return "".join(t.text or "" for t in el.iter(qn("w:t")))
def find(doc, marker, style=None):
    for p in doc.paragraphs:
        if marker in atext(p._element) and (style is None or p.style.name == style):
            return p._element
    return None

def _ins(used):
    ins = etree.Element(qn("w:ins")); ins.set(qn("w:id"), str(nid(used)))
    ins.set(qn("w:author"), AUTHOR); ins.set(qn("w:date"), DATE); return ins

def ins_heading3(num, title, used):
    p = etree.Element(qn("w:p")); pPr = etree.SubElement(p, qn("w:pPr"))
    ps = etree.SubElement(pPr, qn("w:pStyle")); ps.set(qn("w:val"), "Heading3")
    ins = _ins(used); p.append(ins)
    r1 = etree.SubElement(ins, qn("w:r")); t1 = etree.SubElement(r1, qn("w:t")); t1.text = num
    r2 = etree.SubElement(ins, qn("w:r")); etree.SubElement(r2, qn("w:tab"))
    t2 = etree.SubElement(r2, qn("w:t")); t2.set(XS, "preserve"); t2.text = title
    return p

def ins_body(text, used):
    p = etree.Element(qn("w:p")); etree.SubElement(p, qn("w:pPr"))
    ins = _ins(used); p.append(ins)
    r = etree.SubElement(ins, qn("w:r")); t = etree.SubElement(r, qn("w:t"))
    t.set(XS, "preserve"); t.text = text
    return p

def append_ins(p, text, used):
    ins = _ins(used); r = etree.SubElement(ins, qn("w:r")); t = etree.SubElement(r, qn("w:t"))
    t.set(XS, "preserve"); t.text = text; p.append(ins)

def del_run(r, used):
    d = etree.Element(qn("w:del")); d.set(qn("w:id"), str(nid(used)))
    d.set(qn("w:author"), AUTHOR); d.set(qn("w:date"), DATE)
    rc = copy.deepcopy(r)
    for t in rc.findall(qn("w:t")):
        dt = etree.Element(qn("w:delText")); dt.set(XS, "preserve"); dt.text = t.text or ""
        t.getparent().replace(t, dt)
    d.append(rc); return d

def del_para(p, used):
    pPr = p.find(qn("w:pPr"))
    if pPr is None: pPr = etree.Element(qn("w:pPr")); p.insert(0, pPr)
    rPr = pPr.find(qn("w:rPr"))
    if rPr is None: rPr = etree.SubElement(pPr, qn("w:rPr"))
    dm = etree.Element(qn("w:del")); dm.set(qn("w:id"), str(nid(used)))
    dm.set(qn("w:author"), AUTHOR); dm.set(qn("w:date"), DATE); rPr.insert(0, dm)
    for r in p.findall(qn("w:r")):
        p.replace(r, del_run(r, used))

REC = [
 ("5.2.1", "Build the conditions and lead the change",
  f"The most consistent obstacle to value was organizational rather than technical (Section 4.2.1) — "
  f"limited AI literacy, resistance to change, and an inability to think in systems — so managers should "
  f"treat adoption as a change programme rather than a procurement. This means investing in the enabling "
  f"conditions and leading the change directly: educating in a way that is differentiated by level; making "
  f"data and tooling accessible enough for an agent to act within the organization{A}s systems (Section "
  f"4.2.3); stating clearly where the organization is going with AI and what success looks like; bringing "
  f"people along so that the resistance which otherwise stalls adoption is reduced; and identifying, "
  f"empowering, and protecting the AI champions whose visible prototypes attract backing and scale into "
  f"organization-wide initiatives (Section 4.2.2). Above all, managers should create protected, funded space "
  f"for experimentation — accepting that early learning does not always produce immediate returns — because "
  f"tangible value is most reliably discovered by doing rather than planning, and because senior leaders who "
  f"absorb or centralize that cost remove one of the most powerful brakes on adoption."),
 ("5.2.2", "Choose your posture: follow or differentiate",
  "The findings imply a strategic choice between two postures. Much adoption is essentially AI hygiene — "
  "executing proven use cases efficiently to reach parity — and where competitors will inevitably pursue the "
  "same efficiency gains, these are unlikely to confer durable advantage. Pursuing outsized returns instead "
  "requires differentiation: finding novel use cases, experimenting to learn what works, and assembling the "
  "skills to implement them well. Neither posture is inherently wrong, but they demand different investments, "
  "and managers should choose consciously rather than drift; for a structurally resistant organization, even "
  "disciplined following may be the value-maximizing option."),
 ("5.2.3", "Start from the workflow and engineer the configuration",
  f"Value was most reliably created when managers began from a marketing problem or workflow and inserted AI "
  f"where they trusted its performance, rather than adopting AI for its own sake (Section 4.3.1); a practical "
  f"method evident in the data is to decompose a process into its constituent steps and apply agentic AI only "
  f"to the steps where it is reliable, retaining human judgment elsewhere. Because outcomes then depend on "
  f"configuration rather than on the model alone, managers should treat the configuration as the real object "
  f"of design — the harness around the agent (accessible data, memory, tool access, a clear system prompt, and "
  f"guardrails) together with the surrounding data infrastructure and integration with existing systems "
  f"(Section 4.3.2). Designing this deliberately lowers risk and makes the specific contribution of AI "
  f"measurable."),
 ("5.2.4", "Govern AI with AI, calibrated to risk",
  "The same configuration logic offers the most effective response to the risks of agentic AI: deploy AI to "
  "govern AI. Brand-control and tone-of-voice agents can enforce standards at scale, evaluator agents and "
  "human sense-checking can contain hallucination, and benchmarking AI output against a human baseline "
  "converts risk management into a measurable quality process (Sections 4.4.3 and 4.5). Oversight should be "
  "calibrated to the cost of error and the difficulty of evaluating the output, rather than directed at "
  "eliminating error altogether."),
 ("5.2.5", "Resource and source it strategically",
  "Two resourcing decisions recur. First, treat AI budgeting as a strategic act: even in AI-forward "
  "organizations, securing budget remained difficult despite reported returns as high as a tenfold ROI "
  "(Section 4.4.1), and where the upside is large but uncertain and the time to return is variable, "
  "conventional business-case discipline can systematically under-fund experimentation — which is why "
  "centralizing or absorbing the cost of early work, as some leaders did, both resolves the tension and "
  "signals commitment. Second, manage the build-buy-dependence trade-off: external experts and agencies offer "
  "a fast route around scarce internal capacity and multi-year backlogs (Section 4.2.1), but externally "
  "sourced momentum is fragile and over-reliance can leave the AI knowledge built for an organization owned by "
  "its agency, so managers should use external help to accelerate while deliberately retaining and "
  "internalizing capability."),
 ("5.2.6", "Look outward: the agentic demand side and the talent pipeline",
  "Finally, managers should look outward as well as inward. Several participants anticipated agents of "
  "consumers acting as a new intermediary between seller and buyer, and began building connectors so that "
  "their products remain reachable by such agents and visible within AI-mediated search (Sections 4.1.2 and "
  "4.3.1). At the same time, deploying AI first on junior tasks risks eroding the pipeline that develops "
  "juniors into seniors (Section 4.5.4). Managers should weigh short-term efficiency against the longer-term "
  "cost to capability and brand distinctiveness, neither of which is captured by efficiency metrics alone."),
]

def main():
    doc = Document(str(DOCX)); used = used_ids(doc)
    intro = find(doc, "Because value creation with agentic AI depends far more")
    s53 = find(doc, "Limitations & Future research", style="Heading 2")
    assert intro is not None and s53 is not None, "anchors missing"

    # collect the 8 old subsections (everything between intro and the §5.3 heading)
    body = doc.element.body; kids = list(body)
    i0 = kids.index(intro) + 1; i1 = kids.index(s53)
    old = kids[i0:i1]
    assert all(e.tag == qn("w:p") for e in old), "unexpected non-paragraph in §5.2"
    assert len(old) == 16, f"expected 16 old paragraphs (8 head+body), got {len(old)}"

    # intro pointer to Appendix B
    append_ins(intro, " An operational checklist of these implications, organized by the stages of the "
                      "model, is provided in Appendix B.", used)

    # build + insert the six new pairs right after the intro
    new = []
    for num, title, body_txt in REC:
        new.append(ins_heading3(num, title, used)); new.append(ins_body(body_txt, used))
    anchor = intro
    for p in new:
        anchor.addnext(p); anchor = p

    # tracked-delete the eight old subsections
    for e in old:
        del_para(e, used)

    shutil.copy(DOCX, BACKUP); doc.save(str(DOCX))
    print(f"Consolidated §5.2: inserted {len(REC)} recommendations, deleted {len(old)} old paragraphs.")
    print(f"Saved: {DOCX}\nBackup: {BACKUP}")

if __name__ == "__main__":
    main()
