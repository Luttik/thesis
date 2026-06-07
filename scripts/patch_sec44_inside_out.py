# -*- coding: utf-8 -*-
"""
Insert the "inside-out" comparison into the Findings chapter (all tracked, author "Claude").

Edits:
1. §4.3.1 intro  - append a foreshadowing sentence about divergent outcomes.
2. §4 caption    - fix the code-table caption "Table 2" -> "Table 3" (aligns with
                   the in-text references in the Methodology). Bold preserved.
3. §4.4 opening  - replace the two asserted paragraphs ("Notably, even for similar
                   use cases..." and "This is the chapter's central finding...") with:
                   variance paragraph + Table 4 (caption + table) + two vignettes
                   (analytics, content) + an earned, scoped synthesis paragraph.
4. §5 intro      - scope the configuration claim ("where participants could articulate
                   it, the configuration (the 'harness')...").
5. Appendix D    - supporting-quote block behind the comparison.
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
BACKUP    = ROOT / "Thesis Draft - Daan Luttik - MBA.sec44-backup.docx"

AUTHOR = "Claude"
DATE   = "2026-06-07T00:00:00Z"
W      = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"


# --------------------------------------------------------------------------- #
# id helpers
# --------------------------------------------------------------------------- #
def _used_ids(doc) -> set[int]:
    return {int(el.get(qn("w:id"), 0))
            for el in doc.element.body.iter()
            if el.get(qn("w:id")) is not None}

def _nid(used: set[int]) -> int:
    n = max(used, default=0) + 1; used.add(n); return n


def full_text(p_elem) -> str:
    return "".join(t.text or "" for t in p_elem.iter(qn("w:t")))


def find_elem(doc, marker: str):
    for p in doc.paragraphs:
        if marker in full_text(p._element):
            return p._element
    return None


# --------------------------------------------------------------------------- #
# tracked-change builders
# --------------------------------------------------------------------------- #
def ins_run(text: str, used: set[int], bold: bool = False) -> etree._Element:
    ins = etree.Element(qn("w:ins"))
    ins.set(qn("w:id"), str(_nid(used)))
    ins.set(qn("w:author"), AUTHOR)
    ins.set(qn("w:date"), DATE)
    r = etree.SubElement(ins, qn("w:r"))
    if bold:
        rPr = etree.SubElement(r, qn("w:rPr"))
        etree.SubElement(rPr, qn("w:b"))
    t = etree.SubElement(r, qn("w:t"))
    t.set(XMLSPACE, "preserve")
    t.text = text
    return ins


def del_run(r_elem: etree._Element, used: set[int]) -> etree._Element:
    d = etree.Element(qn("w:del"))
    d.set(qn("w:id"), str(_nid(used)))
    d.set(qn("w:author"), AUTHOR)
    d.set(qn("w:date"), DATE)
    rc = copy.deepcopy(r_elem)
    for t in rc.findall(qn("w:t")):
        dt = etree.Element(qn("w:delText"))
        dt.set(XMLSPACE, "preserve")
        dt.text = t.text or ""
        t.getparent().replace(t, dt)
    d.append(rc)
    return d


def ins_para(runs, style: str, used: set[int], block_quote: bool = False) -> etree._Element:
    """runs: list of (text, bold, italic). Whole paragraph wrapped in one <w:ins>."""
    p = etree.Element(qn("w:p"))
    pPr = etree.SubElement(p, qn("w:pPr"))
    if style and style.lower() != "normal":
        ps = etree.SubElement(pPr, qn("w:pStyle")); ps.set(qn("w:val"), style)
    if block_quote:
        ind = etree.SubElement(pPr, qn("w:ind")); ind.set(qn("w:left"), "720")
    ins = etree.SubElement(p, qn("w:ins"))
    ins.set(qn("w:id"), str(_nid(used)))
    ins.set(qn("w:author"), AUTHOR)
    ins.set(qn("w:date"), DATE)
    for text, bold, italic in runs:
        r = etree.SubElement(ins, qn("w:r"))
        if bold or italic:
            rPr = etree.SubElement(r, qn("w:rPr"))
            if bold:   etree.SubElement(rPr, qn("w:b"))
            if italic: etree.SubElement(rPr, qn("w:i"))
        t = etree.SubElement(r, qn("w:t")); t.set(XMLSPACE, "preserve"); t.text = text
    return p


def del_para(p_elem: etree._Element, used: set[int]) -> None:
    """Mark a whole paragraph deleted (runs + paragraph mark), tracked."""
    pPr = p_elem.find(qn("w:pPr"))
    if pPr is None:
        pPr = etree.Element(qn("w:pPr")); p_elem.insert(0, pPr)
    rPr = pPr.find(qn("w:rPr"))
    if rPr is None:
        rPr = etree.SubElement(pPr, qn("w:rPr"))
    dmark = etree.Element(qn("w:del"))
    dmark.set(qn("w:id"), str(_nid(used)))
    dmark.set(qn("w:author"), AUTHOR)
    dmark.set(qn("w:date"), DATE)
    rPr.insert(0, dmark)
    for r in p_elem.findall(qn("w:r")):
        p_elem.replace(r, del_run(r, used))


def replace_text_tracked(p_elem, old: str, new: str, used: set[int]) -> bool:
    for r in p_elem.findall(qn("w:r")):
        t = r.find(qn("w:t"))
        if t is None or not t.text or old not in t.text:
            continue
        before, _, after = t.text.partition(old)
        parent = r.getparent(); idx = list(parent).index(r)
        parts = []
        if before:
            rb = etree.Element(qn("w:r")); tb = etree.SubElement(rb, qn("w:t"))
            tb.set(XMLSPACE, "preserve"); tb.text = before; parts.append(rb)
        d = etree.Element(qn("w:del"))
        d.set(qn("w:id"), str(_nid(used))); d.set(qn("w:author"), AUTHOR); d.set(qn("w:date"), DATE)
        rd = etree.SubElement(d, qn("w:r")); td = etree.SubElement(rd, qn("w:delText"))
        td.set(XMLSPACE, "preserve"); td.text = old
        parts.append(d)
        parts.append(ins_run(new, used))
        if after:
            ra = etree.Element(qn("w:r")); ta = etree.SubElement(ra, qn("w:t"))
            ta.set(XMLSPACE, "preserve"); ta.text = after; parts.append(ra)
        for j, part in enumerate(parts):
            parent.insert(idx + j, part)
        parent.remove(r)
        return True
    return False


def insert_before(anchor, paras) -> None:
    parent = anchor.getparent(); idx = list(parent).index(anchor)
    for i, p in enumerate(paras):
        parent.insert(idx + i, p)


def insert_after(anchor, paras) -> None:
    parent = anchor.getparent(); idx = list(parent).index(anchor) + 1
    for i, p in enumerate(paras):
        parent.insert(idx + i, p)


# --------------------------------------------------------------------------- #
# tracked table builder (Table 4)
# --------------------------------------------------------------------------- #
def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def build_tracked_table(header, rows, widths, used: set[int]) -> etree._Element:
    def ins_attr() -> str:
        return f'w:id="{_nid(used)}" w:author="{AUTHOR}" w:date="{DATE}"'

    def cell(text, width, is_head) -> str:
        if is_head:
            borders = ('<w:top w:val="single" w:sz="7" w:space="0" w:color="000000"/><w:left w:val="nil"/>'
                       '<w:bottom w:val="single" w:sz="7" w:space="0" w:color="000000"/><w:right w:val="nil"/>')
        else:
            borders = '<w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/>'
        bold = '<w:b/><w:bCs/>' if is_head else ''
        body = _esc(text) if text else ' '
        run = (f'<w:r><w:rPr>{bold}<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
               f'<w:t xml:space="preserve">{body}</w:t></w:r>')
        return (f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>'
                f'<w:tcBorders>{borders}</w:tcBorders>'
                f'<w:tcMar><w:top w:w="0" w:type="dxa"/><w:left w:w="100" w:type="dxa"/>'
                f'<w:bottom w:w="0" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tcMar></w:tcPr>'
                f'<w:p><w:pPr><w:spacing w:line="276" w:lineRule="auto"/><w:ind w:firstLine="0"/>'
                f'<w:rPr><w:ins {ins_attr()}/>{bold}<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:pPr>'
                f'<w:ins {ins_attr()}>{run}</w:ins></w:p></w:tc>')

    def row(cells, is_head=False) -> str:
        h = '<w:trHeight w:val="270"/>'
        body = ''.join(cell(c, widths[i], is_head) for i, c in enumerate(cells))
        return f'<w:tr><w:trPr>{h}<w:ins {ins_attr()}/></w:trPr>{body}</w:tr>'

    tblPr = ('<w:tblPr><w:tblStyle w:val="a2"/><w:tblW w:w="8895" w:type="dxa"/>'
             '<w:tblInd w:w="0" w:type="dxa"/>'
             '<w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/>'
             '<w:right w:val="nil"/><w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders>'
             '<w:tblLayout w:type="fixed"/>'
             '<w:tblLook w:val="0600" w:firstRow="0" w:lastRow="0" w:firstColumn="0" '
             'w:lastColumn="0" w:noHBand="1" w:noVBand="1"/></w:tblPr>')
    grid = '<w:tblGrid>' + ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths) + '</w:tblGrid>'
    body = row(header, True) + ''.join(row(r) for r in rows)
    xml = f'<w:tbl xmlns:w="{W}">{tblPr}{grid}{body}</w:tbl>'
    return etree.fromstring(xml.encode("utf-8"))


# --------------------------------------------------------------------------- #
# content
# --------------------------------------------------------------------------- #
LDQ, RDQ, APOS, ELL, MDASH = "“", "”", "’", "…", "—"

VARIANCE = (
    "A pattern cuts across these outcomes: comparable use cases did not produce comparable "
    "results. The same broad application " + MDASH + " an analytics agent, a content pipeline, "
    "a customer-facing assistant " + MDASH + " was reported as transformative in one organization "
    "and as marginal, stalled, or actively counter-productive in another. Because participants "
    "drew on the same generation of widely available models, this variance is not well explained "
    "by the underlying technology; it tracked instead the organizational conditions described in "
    "Section 4.2 and the configuration in which the technology was applied. Table 4 summarizes the "
    "contrast for the three most frequently reported use cases."
)

TBL_HEADER = ["Use case", "Where it created value",
              "Where it stalled or fell short", "The condition that differed"]
TBL_ROWS = [
    ["Self-service analytics",
     "Data sources connected directly to the agent; a reporting request answered in minutes (Interviewees 15, 4)",
     "A capacity-limited tool and a manual upload workaround (Interviewee 3)",
     "Data infrastructure and connectivity (Interviewee 16: a multi-year data-governance track as a precondition)"],
    ["Content and campaigns",
     "Modular, validated, brand-governed pipelines (Interviewees 6, 9, 16)",
     f"Outreach that customers {LDQ}see through{RDQ} (Interviewee 15)",
     f"Validation and brand governance; output worked only where {LDQ}very standardized{RDQ} (Interviewee 11)"],
    ["Customer-facing agents",
     "A deployed chatbot driving retention and upsell (Interviewee 6)",
     "Early or experimental deployments; withheld in a regulated sector (Interviewees 2, 15; 7)",
     "A pre-existing baseline, leadership backing, experimentation, and proving commercial value first"],
]
TBL_WIDTHS = [1660, 2545, 2545, 2145]

ANALYTICS = (
    f"Self-service analytics was the most common use case, yet the experience of it diverged with "
    f"the data infrastructure behind it. Interviewee 15 described a near-frictionless setup: "
    f"{LDQ}with Claude you just connect those data sources directly to Claude […] then everyone can "
    f"really do self-service […] Because it{APOS}s just a question and answer and you get insight.{RDQ} "
    f"Interviewee 4 reported a comparable result after connecting an agent to live data sources, turning "
    f"reporting that once occupied a {LDQ}giant analytics team{RDQ} into a prompt answered "
    f"{LDQ}within ten minutes.{RDQ} Interviewee 3, pursuing the identical goal, met the opposite "
    f"experience: her tool {LDQ}can only digest so much data […] if I try to dump anything over, like, "
    f"30 [megabytes], it […] doesn{APOS}t do it,{RDQ} forcing a manual workaround " + MDASH +
    f" {LDQ}I pull the data from [the warehouse] myself, dump it in, and then have it analyzed{RDQ} " +
    MDASH + f" because the organization{APOS}s data layer was, in her words, {LDQ}not there yet.{RDQ} "
    f"The models were equivalent; the connectivity was not."
)

CONTENT = (
    f"The same divergence appeared within a single organization. Interviewee 11 automated "
    f"{LDQ}about thousand web pages fully automated{RDQ} for one client and judged it a success " +
    MDASH + f" {LDQ}in that use case, it worked. Because it was very standardized.{RDQ} Confronted with "
    f"creative, brand-led work, the same operator using the same tools reached the opposite verdict: "
    f"{LDQ}once you have to have more creativity in the output and also if it needs to be on brand "
    f"[…] AI still falls very very short.{RDQ} Where other participants sustained content quality, they "
    f"did so by configuring the work around the model " + MDASH + " validation, brand and tone-of-voice "
    f"governance, and human oversight (Interviewees 6, 9, and 16). Where that scaffolding was absent, "
    f"the output failed in front of customers; Interviewee 15 recalled an experiment "
    f"{LDQ}generating emails from a BDR to customers{RDQ} in which {LDQ}the customer sees through that "
    f"pretty quickly […] just a bit too much of a shortcut.{RDQ}"
)

SYN_A = "Read together, these contrasts point to the chapter" + APOS + "s central finding: value creation with agentic AI is an "
SYN_B = (
    " process, shaped more by what an organization does with the technology than by which technology it "
    "adopts. Participants located the decisive difference in organizational conditions and managerial "
    f"behaviour " + MDASH + f" Interviewee 9{APOS}s image of an undertaking that succeeds only as "
    f"{LDQ}a whole operational model,{RDQ} {LDQ}like a pie{RDQ} in which {LDQ}you have to have all these "
    f"pieces in order for it to be successful{RDQ}; Interviewee 13{APOS}s caution that {LDQ}GenAI can{APOS}t "
    f"solve any of your problems […] if you […] dump any […] AI tool on a company who has no […] clue about "
    f"what they want to do […] then it will fail.{RDQ} Where they could articulate it more precisely, "
    f"participants located the difference in the configuration " + MDASH + f" the {LDQ}harness{RDQ} around "
    f"the model (Interviewee 5). The benefit, sacrifice, and risk families detailed below should be read in "
    f"this light; their cross-cutting implications are taken up in Chapter 5."
)

FORESHADOW = (
    " Notably, these use cases did not produce uniform results: as Section 4.4 shows, comparable "
    "deployments diverged sharply across organizations, tracking the conditions described in Section 4.2 "
    "rather than the choice of model."
)

APPENDIX_INTRO = ("The quotes below support the comparison in Section 4.4 (Table 4). They are grouped by "
                  "the contrast they illustrate.")

APP_GROUP1 = "Comparable use cases, divergent outcomes"
APP_G1 = [
    ("Interviewee 15, on connecting data sources directly to the agent:",
     f"But just reviewing our entire data infrastructure […] you always want to go toward self-service. "
     f"Yes, but with Claude you just connect those data sources directly to Claude. And then you naturally "
     f"still have some governance to do, but then everyone can really do self-service with that. Because "
     f"it{APOS}s just a question and answer and you get insight."),
    ("Interviewee 4, on an analytics agent wired to live data:",
     "I connected an [agent] to their [analytics and search-console data]. So I have direct access to that "
     "data source […] and I can run cron jobs […] and have an agent run reports and spit that out. And we "
     "got much better reporting […] that was not there because you had to download […] from two different "
     "system[s], then in Excel, you had to cross correlate."),
    ("Interviewee 3, on the same use case under infrastructure constraints:",
     f"[The internal AI tool] can only digest so much data. So if I try to dump anything over, like, "
     f"30 [megabytes], it doesn{APOS}t […] do it. So sometimes I wanna work with […] larger datasets. So "
     f"[…] they{APOS}re working on layering this on top of our data lakes. It{APOS}s not there yet. So in "
     f"the meantime […] I pull the data from [the warehouse] myself, dump it in, and then have it analyzed."),
    ("Interviewee 16, on the governance work that made conversational analytics possible:",
     f"conversational analytics is […] definitely a use case that we{APOS}re working on […] but […] I "
     f"started […] two years ago with a track on […] data governance […] basically describing our business "
     f"definitions […] because I believe that we needed that for the enablement of AI on conversational "
     f"analytics."),
    ("Interviewee 11, on automated content that worked:",
     "we created content for a recruitment organization […] everything there was fully automated. So we "
     "created […] about thousand web pages fully automated. […] in that use case, it worked. Because it was "
     "very standardized."),
    ("Interviewee 11, on the same approach where it fell short:",
     f"once you have to have more creativity in the output and also if it needs to be on brand that AI still "
     f"falls very very short. […] What we really, really stepped away from is […] that AI makes something "
     f"for us without human intervention […] we thought that was scalable, but it{APOS}s not scalable."),
    ("Interviewee 15, on AI-written outreach that backfired:",
     f"There was also an experiment done with generating emails from a BDR to customers. Well, the customer "
     f"sees through that pretty quickly: nice that you still want to be personal and now you{APOS}re sending "
     f"me this, so, just a bit too much of a shortcut with this use case."),
    ("Interviewee 16, on the configuration that protected content quality:",
     f"what we did is we gathered around all the business owners […] one, for example, is […] an add to "
     f"cart. […] I would assume that there{APOS}s one definition of an add to cart […] We got out five "
     f"different definitions of that add to cart. So this is a problem if you want to feed it to AI […] So "
     f"we cleaned up that part with […] agreed-on business definitions."),
    ("Interviewee 6, on a deployed customer-facing chatbot:",
     f"we have a chatbot, she{APOS}s called [Ruby], for our members. And in the chatbot, we{APOS}ve defined "
     f"a lot of conversations where agentic takes over. […] I would say 10X […] Because it{APOS}s not two and "
     f"it{APOS}s also not 200. […] it was really because we had commercial success first […] so now we can "
     f"roll it out throughout the company to other departments."),
    ("Interviewee 7, on why the same use case was withheld in a regulated sector:",
     f"I was in [a major healthcare company], so we used to do a lot of healthcare AI […] but that is the "
     f"most […] regulated side of things […] you can{APOS}t just build a chatbot and throw it in healthcare. "
     f"It needs to go through a lot of scrutiny."),
]

APP_GROUP2 = "Explaining the variance: organization over model"
APP_G2 = [
    ("Interviewee 9, on value as a whole operating model:",
     f"It{APOS}s like a pie. It{APOS}s like you have to have all these pieces in order for it to be "
     f"successful. It can{APOS}t just be successful because the guy at the top building it built this really "
     f"cool product. The […] people have to understand it […] It has to be governed properly, it has to be "
     f"priced properly […] it is a whole operational model that needs to be built around it."),
    ("Interviewee 13, on AI as a multiplier of what an organization already has:",
     f"GenAI can{APOS}t solve any of your problems. GenAI can scale up the concepts you have in mind, the "
     f"knowledge you have, the […] drive that is already there in the company if you use it in the right way. "
     f"So […] if you now dump any […] AI tool on a company who has no […] clue about what they want to do "
     f"[…] then it will fail."),
    ("Interviewee 12, on efficiency as a shared, non-differentiating gain:",
     f"it{APOS}s not a competitive advantage, certainly not in the long term […] but everybody is gonna get "
     f"the benefit of efficiency through AI, so it{APOS}s not really gonna be a way to distinguish yourself "
     f"from your competitors."),
    ("Interviewee 17, on the alignment of conditions:",
     f"leadership wants us to work with AI. But can employees do that too? Do they do it and do they want to? "
     f"Those are basically three things. And when those three things align with each other, you get a "
     f"fantastic AI implementation. But when that{APOS}s not there […] it just stops. And nothing happens."),
    ("Interviewee 14, on the balance of technology and organization:",
     "30% of all AI trajectories is just technology and […] 60% to 70% is […] actually us as humans or as an "
     "organization and therefore also as an ecosystem."),
    ("Interviewee 10, on technology change without organizational change:",
     "a year later, after spending a million, everyone was still working toward exactly the same goals and "
     "producing basically the same output, just with a new system."),
    ("Interviewee 5, on the configuration (the harness) around the model:",
     f"the big change of agentic AI right now is […] very depending on who finds what they call the harness "
     f"[…] who finds the right harness around the AI […] If there{APOS}s a […] party who comes up with a "
     f"really great […] wrapper around the […] product […] that{APOS}s gonna determine a lot of what our "
     f"capabilities are."),
]


def main():
    shutil.copy(DOCX_PATH, BACKUP)
    doc  = Document(str(DOCX_PATH))
    used = _used_ids(doc)

    # Resolve all anchors first (element refs survive structural edits) ------ #
    p_4311    = find_elem(doc, "infrequent but relevant use case")
    p_notably = find_elem(doc, "even for similar use cases")
    p_central = find_elem(doc, "central finding")
    p_captit  = find_elem(doc, "Overview of code development")
    p_sec5    = find_elem(doc, "were reported to produce different outcomes")
    p_appD    = find_elem(doc, "Supporting Quotes")
    for name, el in [("4.3.1", p_4311), ("notably", p_notably), ("central", p_central),
                     ("captiontitle", p_captit), ("sec5", p_sec5), ("appendixD", p_appD)]:
        assert el is not None, f"anchor not found: {name}"
    p_capnum = p_captit.getprevious()
    assert p_capnum is not None and full_text(p_capnum).strip() == "Table 2", \
        f"caption-number paragraph mismatch: {full_text(p_capnum)!r}"

    # 1. §4.3.1 foreshadow (append a tracked run) --------------------------- #
    p_4311.append(ins_run(FORESHADOW, used))
    print("1. foreshadow appended to 4.3.1")

    # 2. caption Table 2 -> Table 3 (tracked, bold preserved) --------------- #
    run = p_capnum.find(qn("w:r"))
    run.addprevious(del_run(run, used))
    run.addprevious(ins_run("Table 3", used, bold=True))
    p_capnum.remove(run)
    print("2. code-table caption renumbered Table 2 -> Table 3")

    # 3. §4.4 replacement --------------------------------------------------- #
    table = build_tracked_table(TBL_HEADER, TBL_ROWS, TBL_WIDTHS, used)
    new_block = [
        ins_para([(VARIANCE, False, False)], "Normal", used),
        ins_para([("Table 4", True, False)], "Normal", used),
        ins_para([("Comparable use cases, divergent outcomes", False, True)], "Normal", used),
        table,
        ins_para([("Analytics. ", True, False), (ANALYTICS, False, False)], "Normal", used),
        ins_para([("Content generation. ", True, False), (CONTENT, False, False)], "Normal", used),
        ins_para([(SYN_A, False, False), ("inside-out", False, True), (SYN_B, False, False)], "Normal", used),
    ]
    insert_before(p_notably, new_block)
    del_para(p_notably, used)
    del_para(p_central, used)
    print("3. §4.4 variance paragraph + Table 4 + vignettes + synthesis inserted; old paras deleted")

    # 4. §5 scope the configuration claim ----------------------------------- #
    ok = replace_text_tracked(
        p_sec5,
        "and the configuration in which the technology was applied rather than to the underlying model",
        "and, where participants could articulate it, the configuration (the " + LDQ + "harness" + RDQ +
        ") in which the technology was applied, rather than to the underlying model",
        used)
    print(f"4. §5 claim scoped: {'ok' if ok else 'FAILED'}")

    # 5. Appendix D --------------------------------------------------------- #
    app = [ins_para([(APPENDIX_INTRO, False, False)], "Normal", used),
           ins_para([(APP_GROUP1, True, False)], "Normal", used)]
    for attr, quote in APP_G1:
        app.append(ins_para([(attr, False, False)], "Normal", used))
        app.append(ins_para([(quote, False, False)], "Normal", used, block_quote=True))
    app.append(ins_para([(APP_GROUP2, True, False)], "Normal", used))
    for attr, quote in APP_G2:
        app.append(ins_para([(attr, False, False)], "Normal", used))
        app.append(ins_para([(quote, False, False)], "Normal", used, block_quote=True))
    insert_after(p_appD, app)
    print(f"5. Appendix D: {len(APP_G1) + len(APP_G2)} supporting quotes inserted")

    doc.save(str(DOCX_PATH))
    print(f"\nSaved: {DOCX_PATH}\nBackup: {BACKUP}")


if __name__ == "__main__":
    main()
