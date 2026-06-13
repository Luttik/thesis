"""
Add supporting interview quotes to Section 4.4 (Obtaining value outcomes).

All changes tracked, author "Claude". Pure insertions (anchors are NOT struck
through) plus one tiny word fix (five -> four themes).

Usage:
    python scripts/patch_sec44_value_quotes.py INPUT.docx OUTPUT.docx
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from lxml import etree

AUTHOR = "Claude"
DATE = "2026-06-12T00:00:00Z"
XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"


# --------------------------------------------------------------------------- #
# id helpers
# --------------------------------------------------------------------------- #
def used_ids(doc) -> set[int]:
    return {int(el.get(qn("w:id"), 0))
            for el in doc.element.body.iter()
            if el.get(qn("w:id")) is not None}


def nid(used: set[int]) -> int:
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
def _ins_elem(text: str, used: set[int]) -> etree._Element:
    ins = etree.Element(qn("w:ins"))
    ins.set(qn("w:id"), str(nid(used)))
    ins.set(qn("w:author"), AUTHOR)
    ins.set(qn("w:date"), DATE)
    r = etree.SubElement(ins, qn("w:r"))
    t = etree.SubElement(r, qn("w:t"))
    t.set(XMLSPACE, "preserve")
    t.text = text
    return ins


def _plain_run(text: str) -> etree._Element:
    r = etree.Element(qn("w:r"))
    t = etree.SubElement(r, qn("w:t"))
    t.set(XMLSPACE, "preserve")
    t.text = text
    return r


def insert_after_anchor(p_elem, anchor: str, new_text: str,
                        used: set[int]) -> bool:
    """Insert `new_text` (tracked) immediately after `anchor`.

    Run-aware: `anchor` may span several runs (quoted phrases are usually their
    own runs). Locates the run holding the END of the anchor, splits it there,
    and inserts a <w:ins> run. Only `new_text` is marked as an insertion; the
    trailing fragment keeps the original run's formatting.
    """
    runs = p_elem.findall(qn("w:r"))
    segs = []  # (run, t_elem, start, end) over concatenated text
    concat = ""
    for r in runs:
        t = r.find(qn("w:t"))
        txt = t.text if (t is not None and t.text) else ""
        segs.append((r, t, len(concat), len(concat) + len(txt)))
        concat += txt

    pos = concat.find(anchor)
    if pos == -1:
        return False
    end = pos + len(anchor)  # char offset where new_text should start

    for r, t, s, e in segs:
        if t is None:
            continue
        if s < end <= e:
            local = end - s
            before, after = t.text[:local], t.text[local:]
            parent = r.getparent()
            idx = list(parent).index(r)
            t.text = before
            parts = [_ins_elem(new_text, used)]
            if after:
                rc = copy.deepcopy(r)          # preserve original rPr
                rc.find(qn("w:t")).text = after
                parts.append(rc)
            for j, part in enumerate(parts):
                parent.insert(idx + 1 + j, part)
            return True
    return False


def replace_word_tracked(p_elem, old: str, new: str, used: set[int]) -> bool:
    """Tracked del(old)+ins(new) for a short token within one run."""
    for r in p_elem.findall(qn("w:r")):
        t = r.find(qn("w:t"))
        if t is None or not t.text or old not in t.text:
            continue
        before, _, after = t.text.partition(old)
        parent = r.getparent()
        idx = list(parent).index(r)
        t.text = before
        d = etree.Element(qn("w:del"))
        d.set(qn("w:id"), str(nid(used)))
        d.set(qn("w:author"), AUTHOR)
        d.set(qn("w:date"), DATE)
        rd = etree.SubElement(d, qn("w:r"))
        dt = etree.SubElement(rd, qn("w:delText"))
        dt.set(XMLSPACE, "preserve")
        dt.text = old
        parts = [d, _ins_elem(new, used)]
        if after:
            parts.append(_plain_run(after))
        for j, part in enumerate(parts):
            parent.insert(idx + 1 + j, part)
        return True
    return False


# --------------------------------------------------------------------------- #
# edits  (anchor_tail, new_text)
# --------------------------------------------------------------------------- #
# curly quotes throughout to match house typography
LQ, RQ = "“", "”"
APO = "’"
ELL = "…"

EDITS = [
    # 4.4.1 Efficiency – add concrete magnitude (I3)
    ("This might take the form of doing more with the same amount of effort.",
     f" Interviewee 3 put a concrete figure on this, describing analysis that "
     f"{LQ}would{APO}ve taken, like, a week to put together{RQ} now turned around "
     f"{LQ}within, like, two hours.{RQ}"),

    # 4.4.1 Speed – add responsiveness angle (I4)
    (f"you have the ability to run more experiments.{RQ}",
     f" Speed also shortens how quickly an organization can react to its market: "
     f"interviewee 4 set up {LQ}competition research agents that come back with every "
     f"change that they made on their landing page, pricing, et cetera, so you can "
     f"respond faster.{RQ}"),

    # 4.4.1 Scale – add concrete magnitudes (I8, I9)
    ("automating processes that would take manual effort.",
     f" The magnitudes described are striking. Interviewee 8, asked how his team "
     f"produced advertising at scale, recalled that copy which {LQ}would take probably "
     f"about a year{RQ} by hand was generated {LQ}within{ELL} a week{RQ} through an AI "
     f"workflow. Interviewee 9 stressed that scale also means variation no person can "
     f"match: {LQ}a human can only think in so many{ELL} variations,{RQ} whereas the "
     f"system {LQ}can create all these different versions of a campaign.{RQ}"),

    # 4.4.1 Skillset – add seniority-shift angle (I7)
    ("the social media manager “suddenly becomes a designer and app concept creator.”",
     f" The same dynamic reshapes the seniority mix of work: interviewee 7 reframed the "
     f"business case around AI-augmented juniors, noting that where a campaign once "
     f"required two senior marketers, {LQ}I don{APO}t need two of those guys, I need one, "
     f"a junior, and he can do the same thing.{RQ}"),

    # 4.4.1 Quality – AI can exceed human quality (I14)
    ("improving the quality compared to the human-made originals.",
     f" Interviewee 14 went further, observing that such output {LQ}is often even better "
     f"than the quality that is ultimately{ELL} made by{ELL} people.{RQ}"),

    # 4.4.2 Costs – scale of investment + subsidised prices (I9, I16)
    ("That’s something that we don’t take into consideration.”",
     f" The scale of commitment can be substantial: interviewee 9 noted her agency had "
     f"invested {LQ}millions{ELL} in our{ELL} agentic{ELL} tool chain.{RQ} Several "
     f"participants also cautioned that current prices understate the eventual cost; "
     f"interviewee 16 observed that {LQ}a lot of AI is subsidized now{RQ} and expected "
     f"that {LQ}these prices will go up{RQ} as the market matures."),

    # 4.4.2 Job displacement – job morphs rather than disappears (I4)
    ("In other examples, interviewees describe more or different work being picked up.",
     f" Interviewee 4 framed the shift as transformation rather than elimination: "
     f"{LQ}people should be very afraid{ELL} that their job is totally going to be "
     f"different. And if you don{APO}t{ELL} change with the job, you find yourself out "
     f"of a job.{RQ}"),

    # 4.4.3 Security & privacy – add breadth of voices (I9, I2)
    ("any violation of law, policy, or user’s trust regarding security and privacy.",
     f" The worry spans both in-house teams and agencies: interviewee 9 framed it as "
     f"clients {LQ}being concerned that their{ELL} PII{ELL} is gonna go into an AI tool,"
     f"{RQ} while interviewee 2 stressed the need for {LQ}maximum privacy and security in "
     f"place,{RQ} keeping data {LQ}secure{RQ} and {LQ}closed.{RQ}"),

    # 4.4.3 Brand – capability-blurring risk that sets up the closing argument (I10)
    ("she noted it was “just a bit too much of a shortcut with this use case”",
     f". Interviewee 10 tied the risk to the blurring of who can now produce brand "
     f"assets, warning of {LQ}slick content made by someone who doesn{APO}t understand "
     f"the brand,{RQ} which he called {LQ}a real risk with capability blurring.{RQ}"),
]


def main():
    inp, outp = Path(sys.argv[1]), Path(sys.argv[2])
    doc = Document(str(inp))
    used = used_ids(doc)

    # word fix: five -> four themes
    p = find_para(doc, "cluster around five themes")
    ok = replace_word_tracked(p, "five themes", "four themes", used) if p is not None else False
    print(f"[fix ] five->four themes: {'OK' if ok else 'FAILED'}")

    for anchor, new_text in EDITS:
        # locate the paragraph that contains the anchor
        target = find_para(doc, anchor)
        if target is None:
            print(f"[MISS] anchor not found: {anchor[:60]!r}")
            continue
        ok = insert_after_anchor(target, anchor, new_text, used)
        print(f"[{'ins ' if ok else 'FAIL'}] {anchor[:60]!r}")

    doc.save(str(outp))
    print(f"\nSaved: {outp}")


if __name__ == "__main__":
    main()
