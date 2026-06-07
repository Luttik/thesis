# -*- coding: utf-8 -*-
"""Phase 1: renumber appendices C->B and D->C (tracked, format-preserving).
Phase 2: insert a new 'Appendix D — a manager's checklist', keyed to the five stages
of the value-creation model (Figure 1), before the 'Appendix E. What to include?' heading.
Tracked, author 'Claude'. All-or-nothing save."""
from __future__ import annotations
import copy, shutil
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP = ROOT / "Thesis Draft - Daan Luttik - MBA.appF-backup.docx"
AUTHOR = "Claude"; DATE = "2026-06-07T17:00:00Z"
XS = "{http://www.w3.org/XML/1998/namespace}space"
BOX = "☐ "

def used_ids(doc):
    return {int(el.get(qn("w:id"), 0)) for el in doc.element.body.iter() if el.get(qn("w:id")) is not None}
def nid(u): n = max(u, default=0) + 1; u.add(n); return n
def acc(p): return "".join(t.text or "" for t in p.iter(qn("w:t")))

def find_heading(doc, *needles):
    for p in doc.paragraphs:
        t = acc(p._element)
        if p.style.name.startswith("Heading") and all(n in t for n in needles):
            return p._element
    return None

def ins_para(text, style, used):
    p = etree.Element(qn("w:p")); pPr = etree.SubElement(p, qn("w:pPr"))
    if style:
        ps = etree.SubElement(pPr, qn("w:pStyle")); ps.set(qn("w:val"), style)
    ins = etree.SubElement(p, qn("w:ins"))
    ins.set(qn("w:id"), str(nid(used))); ins.set(qn("w:author"), AUTHOR); ins.set(qn("w:date"), DATE)
    r = etree.SubElement(ins, qn("w:r")); t = etree.SubElement(r, qn("w:t"))
    t.set(XS, "preserve"); t.text = text
    return p

def _ins_run(text, used, rpr=None):
    ins = etree.Element(qn("w:ins")); ins.set(qn("w:id"), str(nid(used)))
    ins.set(qn("w:author"), AUTHOR); ins.set(qn("w:date"), DATE)
    r = etree.SubElement(ins, qn("w:r"))
    if rpr is not None: r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, qn("w:t")); t.set(XS, "preserve"); t.text = text
    return ins

def replace_keepfmt(p_elem, old, new, used):
    """Tracked replace of `old`->`new`; the inserted run inherits the matched run's rPr
    (so a renamed heading letter keeps heading formatting)."""
    runs = p_elem.findall(qn("w:r")); segs, total = [], ""
    for r in runs:
        t = r.find(qn("w:t")); txt = t.text if (t is not None and t.text) else ""
        segs.append((r, txt)); total += txt
    start = total.find(old)
    if start < 0: return False
    end = start + len(old)
    def mk(rPr, s):
        nr = etree.Element(qn("w:r"))
        if rPr is not None: nr.append(copy.deepcopy(rPr))
        tt = etree.SubElement(nr, qn("w:t")); tt.set(XS, "preserve"); tt.text = s; return nr
    def mkdel(rPr, s):
        d = etree.Element(qn("w:del")); d.set(qn("w:id"), str(nid(used)))
        d.set(qn("w:author"), AUTHOR); d.set(qn("w:date"), DATE)
        dr = etree.SubElement(d, qn("w:r"))
        if rPr is not None: dr.insert(0, copy.deepcopy(rPr))
        dt = etree.SubElement(dr, qn("w:delText")); dt.set(XS, "preserve"); dt.text = s; return d
    pos, inserted = 0, False
    for r, txt in segs:
        rs, re_ = pos, pos + len(txt); pos = re_
        if not txt or re_ <= start or rs >= end: continue
        rPr = r.find(qn("w:rPr")); ls = max(start, rs) - rs; le = min(end, re_) - rs
        before, deleted, after = txt[:ls], txt[ls:le], txt[le:]
        parent = r.getparent(); idx = list(parent).index(r); parts = []
        if before: parts.append(mk(rPr, before))
        if not inserted: parts.append(_ins_run(new, used, rpr=rPr)); inserted = True
        if deleted: parts.append(mkdel(rPr, deleted))
        if after: parts.append(mk(rPr, after))
        for j, prt in enumerate(parts): parent.insert(idx + j, prt)
        parent.remove(r)
    return inserted

# ---------------------------------------------------------------- content ----
TITLE = "Appendix D. Putting the model to work: a manager’s checklist"
INTRO = ("This appendix translates the practical implications of Section 5.2 into an operational "
         "checklist, organized by the five stages of the value-creation model developed in Chapter 4 "
         "(Figure 1): observing the external context, auditing the organizational conditions, steering "
         "the organization, applying agentic AI, and mediating the flow through to value outcomes. It is "
         "intended as a working tool — a marketing manager can use it to audit where an agentic-AI "
         "initiative is strong and where it is exposed. The items distil patterns reported across the "
         "interviews in Chapter 4; not every item will apply to every organization.")

SECTIONS = [
    ("Observing — sensing the changing context", [
        "Watch the emerging use cases, and the combinations of tool (or approach) with use case — value tends to lie in the pairing, not in the tool alone.",
        "Track AI’s capability progression, but treat tool- and model-specific facts as dating within months.",
        "Monitor competitors’ adoption of agentic AI.",
        "Monitor shifts in consumer behaviour, including customers acting through their own agents (“agents of customers”).",
        "Read vendor roadmaps, but separate what is operationally available from what is merely announced.",
        "Test each reported “use case” for whether it is actually in production and creating value, rather than hype or optics — whether it is “truly agentic” is beside the point.",
        "Make observation collective — for example, a recurring internal AI sparring group — rather than leaving sensing to chance.",
    ]),
    ("Conditions — auditing what enables or constrains", [
        "Assess AI literacy at every level and locate resistance, analysis paralysis, and gaps in systems thinking.",
        "Audit data availability, infrastructure, and the technical talent to use them; an agent cannot reach what the organization has not made accessible.",
        "Confirm strategic direction and secure senior-leadership backing before scaling.",
        "Map governance, legal, and compliance constraints (such as GDPR) and the political silos that slow delivery.",
        "Resolve definitional ambiguity early: agree shared business definitions and a data catalogue as a precondition for reliable AI.",
    ]),
    ("Steering — acting on the conditions", [
        "Reshape what you control: educate (differentiated by level), run experiments, bring people along, provide clarity, and champion the work.",
        "Leverage what is favourable: accessible data, good tooling, an innovation culture, and credible external experts.",
        "Where you cannot reshape a constraint, create room within it rather than only working around it — for example, a protected laboratory or sandbox, separated from the production environment, where experiments can fail safely, promoting only proven use cases into production.",
        "Identify, empower, and protect AI champions who combine technical and business fluency.",
        "Fund and protect experimentation: centralize or absorb its cost so teams are not penalized for early, low-return learning.",
        "Use external help to accelerate, but deliberately retain and internalize capability to avoid dependence.",
    ]),
    ("Applying — putting agentic AI to work", [
        "Start from a marketing problem or workflow, not from the technology; adopt AI for a job, not for its own sake.",
        "Decompose the workflow into steps and insert AI only where you trust its performance; keep humans where you do not.",
        "Engineer the harness as the real object of design: accessible data, memory, tool access, a clear system prompt, and guardrails.",
        "Standardize or clearly define a task before automating it; automated content works where output is standardized and falls short on creative, on-brand work.",
        "Match ambition to maturity across use cases (analytics, content, generic agents, customer-facing).",
        "For customer-facing agents, build on an existing baseline, put brand and tone-of-voice governance in place first, prove commercial value, and then scale.",
        "Make the build, buy, or off-the-shelf choice explicitly, weighing speed against lock-in.",
    ]),
    ("Mediating the flow to outcomes — turning application into value", [
        "State the value you are pursuing (efficiency, scale, skill extension, quality) and benchmark AI output against a human baseline so improvement is measurable.",
        "Account honestly for sacrifices: infrastructure, API, and licensing costs, the time to implement, and the human impact of any displacement.",
        "Govern risks with AI: brand-control and tone-of-voice agents for brand risk; evaluator agents and human sense-checking for hallucination; explicit controls for security and privacy.",
        "Calibrate oversight to the cost of error and the difficulty of evaluating the output, not to eliminating error altogether.",
        "Decide consciously whether to follow (efficiency parity) or to differentiate (novel use cases); efficiency gains are not a durable advantage once competitors share them.",
        "Treat AI budgeting as a strategic act: returns can be large but uncertain, and conventional business cases tend to under-fund experimentation.",
        "Protect the longer term: do not hollow out the junior talent pipeline or trade away brand distinctiveness for short-term efficiency.",
    ]),
]


def main():
    doc = Document(str(DOCX)); used = used_ids(doc)

    # ---- Phase 1: renumber C->B and D->C ----
    el_b = find_heading(doc, "Appendix C", "constructive grounded theory")
    el_c = find_heading(doc, "Appendix D", "Supporting Quotes")
    assert el_b is not None, "CGT appendix heading not found"
    assert el_c is not None, "Supporting Quotes appendix heading not found"
    r1 = replace_keepfmt(el_b, "Appendix C", "Appendix B", used)
    r2 = replace_keepfmt(el_c, "Appendix D", "Appendix C", used)
    assert r1 and r2, f"rename failed (C->B={r1}, D->C={r2})"
    print("Phase 1: renamed Appendix C->B (CGT) and D->C (Supporting Quotes)")

    # ---- Phase 2: insert new Appendix D before 'Appendix E. What to include?' ----
    anchor = find_heading(doc, "What to include")
    assert anchor is not None, "'Appendix E. What to include?' heading not found"
    paras = [ins_para(TITLE, "Heading1", used), ins_para(INTRO, None, used)]
    n_items = 0
    for head, items in SECTIONS:
        paras.append(ins_para(head, "Heading2", used))
        for it in items:
            paras.append(ins_para(BOX + it, None, used)); n_items += 1
    for p in paras:
        anchor.addprevious(p)
    print(f"Phase 2: inserted Appendix D with {len(SECTIONS)} sections, {n_items} checklist items")

    shutil.copy(DOCX, BACKUP); doc.save(str(DOCX))
    print(f"\nSaved: {DOCX}\nBackup: {BACKUP}")


if __name__ == "__main__":
    main()
