# -*- coding: utf-8 -*-
"""
Extensive proofread pass across Executive Summary, Ch1, Ch2, Ch4, Ch5, Ch6
(Ch3 was already done in a prior pass). Tracked changes + comments, author
"Claude". Scope excludes: Foreword (personal/memoir voice), References,
Appendices, and -- critically -- the WORDS of any direct interview quote
(only the author's own analytical/connecting prose is touched).

Three edit mechanisms:
  1. replace_text_tracked - single-run substring replace (old -> new). If
     new == "", it's a pure tracked deletion (no <w:ins> emitted).
  2. replace_span_tracked - general version that may cross multiple direct
     runs (needed once, for the garbled/duplicate sentence in para 301).
  3. comment_on_plain_substr - anchors a review comment to a substring
     inside a single plain run, no text change.

One edit (para 188) needs a curly-quote-safe dynamic anchor: the `old`
string is sliced live from the run's own text via .index(), never hand-typed,
to avoid any risk of mistyping the document's curly quotes/apostrophes.
"""
from __future__ import annotations

import copy
import shutil
import zipfile
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from lxml import etree

ROOT   = Path(__file__).resolve().parents[1]
DOCX   = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP = ROOT / "Thesis Draft - Daan Luttik - MBA.allch-proofread-backup.docx"
TEMP   = ROOT / "Thesis Draft - Daan Luttik - MBA.allch-proofread-tmp.docx"

W   = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
W15 = "http://schemas.microsoft.com/office/word/2012/wordml"
W16 = "http://schemas.microsoft.com/office/word/2016/wordml/cid"
XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"

AUTHOR, INITIALS, DATE = "Claude", "C", "2026-07-09T00:00:00Z"


def w(t):   return f"{{{W}}}{t}"
def w14(t): return f"{{{W14}}}{t}"
def w15(t): return f"{{{W15}}}{t}"
def w16(t): return f"{{{W16}}}{t}"


# --------------------------------------------------------------------------- #
# id + element builders
# --------------------------------------------------------------------------- #
def _used_ids(doc) -> set[int]:
    return {int(el.get(qn("w:id"), 0))
            for el in doc.element.body.iter()
            if el.get(qn("w:id")) is not None}


def _nid(used: set[int]) -> int:
    n = max(used, default=0) + 1
    used.add(n)
    return n


def clone_rpr(r_elem):
    rpr = r_elem.find(qn("w:rPr"))
    return copy.deepcopy(rpr) if rpr is not None else None


def mk_plain_run(text, rpr):
    r = etree.Element(qn("w:r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, qn("w:t")); t.set(XMLSPACE, "preserve"); t.text = text
    return r


def mk_ins_run(text, rpr, used):
    ins = etree.Element(qn("w:ins"))
    ins.set(qn("w:id"), str(_nid(used))); ins.set(qn("w:author"), AUTHOR); ins.set(qn("w:date"), DATE)
    r = etree.SubElement(ins, qn("w:r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, qn("w:t")); t.set(XMLSPACE, "preserve"); t.text = text
    return ins


def mk_del_run(text, rpr, used):
    d = etree.Element(qn("w:del"))
    d.set(qn("w:id"), str(_nid(used))); d.set(qn("w:author"), AUTHOR); d.set(qn("w:date"), DATE)
    r = etree.SubElement(d, qn("w:r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    dt = etree.SubElement(r, qn("w:delText")); dt.set(XMLSPACE, "preserve"); dt.text = text
    return d


def get_run_text(r):
    t = r.find(qn("w:t"))
    return t.text if (t is not None and t.text) else ""


# --------------------------------------------------------------------------- #
# tracked-change edits
# --------------------------------------------------------------------------- #
def replace_text_tracked(p_elem, old: str, new: str, used: set[int]) -> bool:
    """Single-run substring replace. new == '' -> pure deletion (no <w:ins>)."""
    for r in p_elem.findall(qn("w:r")):
        t = r.find(qn("w:t"))
        if t is None or not t.text or old not in t.text:
            continue
        rpr = clone_rpr(r)
        before, _, after = t.text.partition(old)
        parent = r.getparent()
        idx = list(parent).index(r)
        parts = []
        if before:
            parts.append(mk_plain_run(before, rpr))
        parts.append(mk_del_run(old, rpr, used))
        if new:
            parts.append(mk_ins_run(new, rpr, used))
        if after:
            parts.append(mk_plain_run(after, rpr))
        for j, part in enumerate(parts):
            parent.insert(idx + j, part)
        parent.remove(r)
        return True
    return False


def replace_span_tracked(p_elem, old: str, new: str, used: set[int]) -> bool:
    """Like replace_text_tracked but `old` may span multiple direct runs."""
    runs = p_elem.findall(qn("w:r"))
    texts = [get_run_text(r) for r in runs]
    full = "".join(texts)
    start = full.find(old)
    if start == -1:
        return False
    end = start + len(old)

    cum = 0
    start_ri = start_off = end_ri = end_off = None
    for i, tx in enumerate(texts):
        run_start, run_end = cum, cum + len(tx)
        if start_ri is None and run_start <= start < run_end:
            start_ri, start_off = i, start - run_start
        if end_ri is None and run_start < end <= run_end:
            end_ri, end_off = i, end - run_start
        cum = run_end
    if start_ri is None or end_ri is None:
        return False

    replacement = []
    if start_ri == end_ri:
        tx, rpr = texts[start_ri], clone_rpr(runs[start_ri])
        pre, mid, suf = tx[:start_off], tx[start_off:end_off], tx[end_off:]
        if pre:
            replacement.append(mk_plain_run(pre, rpr))
        if new:
            replacement.append(mk_ins_run(new, rpr, used))
        if mid:
            replacement.append(mk_del_run(mid, rpr, used))
        if suf:
            replacement.append(mk_plain_run(suf, rpr))
    else:
        first_tx, first_rpr = texts[start_ri], clone_rpr(runs[start_ri])
        pre, mid0 = first_tx[:start_off], first_tx[start_off:]
        if pre:
            replacement.append(mk_plain_run(pre, first_rpr))
        if new:
            replacement.append(mk_ins_run(new, first_rpr, used))
        if mid0:
            replacement.append(mk_del_run(mid0, first_rpr, used))
        for i in range(start_ri + 1, end_ri):
            if texts[i]:
                replacement.append(mk_del_run(texts[i], clone_rpr(runs[i]), used))
        last_tx, last_rpr = texts[end_ri], clone_rpr(runs[end_ri])
        mid1, suf = last_tx[:end_off], last_tx[end_off:]
        if mid1:
            replacement.append(mk_del_run(mid1, last_rpr, used))
        if suf:
            replacement.append(mk_plain_run(suf, last_rpr))

    parent = runs[start_ri].getparent()
    idx = list(parent).index(runs[start_ri])
    for i in range(start_ri, end_ri + 1):
        parent.remove(runs[i])
    for j, node in enumerate(replacement):
        parent.insert(idx + j, node)
    return True


# --------------------------------------------------------------------------- #
# comment-range helpers
# --------------------------------------------------------------------------- #
def crs(cid):
    e = etree.Element(qn("w:commentRangeStart")); e.set(qn("w:id"), str(cid)); return e

def cre(cid):
    e = etree.Element(qn("w:commentRangeEnd")); e.set(qn("w:id"), str(cid)); return e

def cref(cid):
    r = etree.Element(qn("w:r"))
    rpr = etree.SubElement(r, qn("w:rPr"))
    etree.SubElement(rpr, qn("w:rStyle")).set(qn("w:val"), "CommentReference")
    etree.SubElement(r, qn("w:commentReference")).set(qn("w:id"), str(cid))
    return r


def comment_on_plain_substr(p_elem, substr, cid) -> bool:
    for r in p_elem.findall(qn("w:r")):
        t = r.find(qn("w:t"))
        if t is None or not t.text or substr not in t.text:
            continue
        rpr = clone_rpr(r)
        before, _, after = t.text.partition(substr)
        parent = r.getparent()
        idx = list(parent).index(r)
        seq = []
        if before:
            seq.append(mk_plain_run(before, rpr))
        seq.append(crs(cid))
        seq.append(mk_plain_run(substr, rpr))
        seq.append(cre(cid))
        seq.append(cref(cid))
        if after:
            seq.append(mk_plain_run(after, rpr))
        for j, el in enumerate(seq):
            parent.insert(idx + j, el)
        parent.remove(r)
        return True
    return False


def add_comment_entry(com_t, cex_t, cid_t, cid, paraid, durable, text):
    c = etree.SubElement(com_t, w("comment"))
    c.set(w("id"), str(cid)); c.set(w("author"), AUTHOR); c.set(w("date"), DATE); c.set(w("initials"), INITIALS)
    p = etree.SubElement(c, w("p")); p.set(w14("paraId"), paraid); p.set(w14("textId"), "77777777")
    etree.SubElement(etree.SubElement(p, w("pPr")), w("pStyle")).set(w("val"), "CommentText")
    r1 = etree.SubElement(p, w("r"))
    etree.SubElement(etree.SubElement(r1, w("rPr")), w("rStyle")).set(w("val"), "CommentReference")
    etree.SubElement(r1, w("annotationRef"))
    r2 = etree.SubElement(p, w("r"))
    t = etree.SubElement(r2, w("t")); t.set(XMLSPACE, "preserve"); t.text = text
    etree.SubElement(cex_t, w15("commentEx")).attrib.update({w15("paraId"): paraid, w15("done"): "0"})
    etree.SubElement(cid_t, w16("commentId")).attrib.update({w16("paraId"): paraid, w16("durableId"): durable})


# --------------------------------------------------------------------------- #
# EDITS  (para_index, old, new) -- single-run, left-to-right per paragraph
# --------------------------------------------------------------------------- #
EDITS = [
    # Executive Summary + Chapter 1
    (51, "And in doing so", "In doing so"),
    (51, "empirical works", "empirical accounts"),
    (57, "2025).  The use of GenAI", "2025). The use of GenAI"),
    (60, "  ", " "),
    (60, "large amount of daily tasks", "large number of daily tasks"),
    (64, "call to research Kim", "call for research, Kim"),
    (65, "(2022); but they were not written", "(2022), but they were not written"),
    (66, "obtaining the resulting value creation.", "obtaining the resulting value outcomes."),
    (66, "within the related fields of GenAI and digital transformation",
         "within the related fields of GenAI and digital transformation."),
    # Chapter 2
    (71, "tasks that are typically associated with human cognition",
         "tasks typically requiring human cognition"),
    (71, "AI can be broadly categorized into two categories:", "AI can be broadly divided into two categories:"),
    (76, "2012).  Probably", "2012). Probably"),
    (78, "But the real breakthrough", "However, the real breakthrough"),
    (78, "2019), this model was often applied", "2019); this model was often applied"),
    (80, "BERT focused on classification", "BERT focuses on classification"),
    (86, " This ability to act results in a situation where an AI agent can work within "
         "systems at the behest of the user (Hughes et al., 2025).", ""),
    (92, "2. the ability", "2. The ability"),
    (96, "which Agentic AI is evolving", "which agentic AI is evolving"),
    # Chapter 4
    (176, "guidance. ", "guidance."),
    (229, "  T", " T"),
    (232, "  He wonders", " He wonders"),
    (234, "component.  ", "component. "),
    (237, "  Interviewee 12", " Interviewee 12"),
    (264, "Table 5", "Table 5."),
    (265, "divergent outcomes", "divergent outcomes."),
    # Chapter 5 + 6
    (269, "agentic AI. ", "agentic AI."),
    (277, "  The impetus", " The impetus"),
    (281, ", we observed", ". We observed"),
    (281, "a range ", "a range"),
    (301, "research study specific elements", "research into study-specific elements"),
    (301, "affect business outcomes, this research might", "affect business outcomes; this research might"),
]

# multi-run span edits (old may cross direct-run boundaries, e.g. two adjacent
# single-space runs, or a longer deletion)
SPAN_EDITS = [
    (299, "  ", " "),  # double space split across two separate single-space runs
    (301,
     " how s seems to rarely analyze the impact of specific technical features or technical "
     "configurations on business outcomes; research in this domain could further explain the "
     "high variance regarding value outcomes for similar use cases. ",
     ""),
]

# (para_index, anchor_substr, comment_text)
T_C_STAT = ("Cross-check: this figure (Mayer et al., 2025) is described here as '~one-third of the "
            "estimated $4.4 trillion in annual productivity growth,' but the Executive Summary "
            "describes the same citation as 'roughly a third of AI's economic value.' Worth confirming "
            "both phrasings accurately reflect the source and are consistent with each other.")
T_C_86 = ("Deleted the final sentence here: it restated the same point as the sentence before it (both "
          "say the ability to act lets agents work within/affect systems on the user's behalf, same "
          "citation). Flagging in case the second sentence was meant to add something distinct.")
T_C_188 = ("Trimmed the repeated 'CTO's best friend' quote/explanation here: it's the same interviewee, "
           "same quote, same point already made one paragraph earlier (4.2.2's opening). Kept this "
           "paragraph's non-redundant content (no clear pattern of altering these conditions).")
T_C_297 = ("This sentence ('digital leaders should become business leaders' / 'marketing leaders should "
           "also become digital leaders...') is close to verbatim the same claim made in 5.1 "
           "(paragraph on Fernandez-Vidal et al., 2022). Consider stating it once and cross-referencing "
           "from the other section.")
T_C_301 = ("Found a garbled, duplicated sentence here starting 'how s seems to rarely analyze...' -- it "
           "restated the same point as the sentence before it (this research doesn't examine how "
           "technical features/configurations affect outcomes) and contained what looks like a typo "
           "fragment ('how s'). Deleted it; also fixed the comma splice in the sentence it duplicated.")

COMMENTS = [
    (57,  "substr", "one-third of the estimated $4.4 trillion in annual productivity growth", T_C_STAT),
    (86,  "substr", "affect business applications", T_C_86),
    (188, "substr", "no clear patterns of", T_C_188),
    (297, "substr", "should become business leade", T_C_297),
    (301, "substr", "from similar use cases", T_C_301),
]


def main():
    with zipfile.ZipFile(DOCX) as z:
        com0 = etree.fromstring(z.read("word/comments.xml"))
        cex0 = etree.fromstring(z.read("word/commentsExtended.xml"))
        cid0 = etree.fromstring(z.read("word/commentsIds.xml"))
    next_cid = max(int(c.get(w("id"))) for c in com0.findall(w("comment"))) + 1
    used_paraids = {p.get(w14("paraId"), "").upper()
                    for c in com0.findall(w("comment")) for p in c.iter(w("p"))}
    used_paraids |= {e.get(w15("paraId"), "").upper() for e in cex0}
    max_dur = max(int(x.get(w16("durableId")), 16) for x in cid0)

    def fresh_paraid(seed):
        v = seed
        while ("%08X" % v) in used_paraids:
            v += 1
        used_paraids.add("%08X" % v)
        return "%08X" % v

    reserved = []
    for i in range(len(COMMENTS)):
        reserved.append((next_cid + i, fresh_paraid(0x0C300001 + i), "%08X" % (max_dur + 1 + i)))

    doc = Document(str(DOCX))
    paras = doc.paragraphs
    used_rev = _used_ids(doc)

    # dynamic, curly-quote-safe anchor for the para-188 trim (computed from live text)
    r4_188 = paras[188]._element.findall(qn("w:r"))[-1]
    r4_188_text = get_run_text(r4_188)
    old_188 = r4_188_text[r4_188_text.index("other teams;"):]
    dynamic_edits = [(188, old_188, "other teams outside the marketing department’s direct control.")]

    print("=== single-run edits ===")
    failures = []
    for idx, old, new in EDITS + dynamic_edits:
        ok = replace_text_tracked(paras[idx]._element, old, new, used_rev)
        print(f"[{'OK ' if ok else 'MISS'}] para {idx}: {old!r} -> {new!r}")
        if not ok:
            failures.append((idx, old))

    print("\n=== span edits ===")
    for idx, old, new in SPAN_EDITS:
        ok = replace_span_tracked(paras[idx]._element, old, new, used_rev)
        print(f"[{'OK ' if ok else 'MISS'}] para {idx}: span delete/replace ({len(old)} chars)")
        if not ok:
            failures.append((idx, old[:60]))

    print("\n=== comments ===")
    for (idx, kind, arg, _), (cid, paraid, durable) in zip(COMMENTS, reserved):
        ok = comment_on_plain_substr(paras[idx]._element, arg, cid)
        print(f"[{'OK ' if ok else 'MISS'}] comment {cid} -> para {idx}: {arg!r}")
        if not ok:
            failures.append((idx, arg))

    if failures:
        print(f"\nABORT: {len(failures)} failure(s); NOT saving.")
        for idx, what in failures:
            print(f"   miss para {idx}: {what!r}")
        return

    shutil.copy(DOCX, BACKUP)
    doc.save(str(TEMP))

    with zipfile.ZipFile(TEMP) as z:
        names = z.namelist()
        blobs = {n: z.read(n) for n in names}

    com_t = etree.fromstring(blobs["word/comments.xml"])
    cex_t = etree.fromstring(blobs["word/commentsExtended.xml"])
    cid_t = etree.fromstring(blobs["word/commentsIds.xml"])

    for (_, _, _, text), (cid, paraid, durable) in zip(COMMENTS, reserved):
        add_comment_entry(com_t, cex_t, cid_t, cid, paraid, durable, text)

    def ser(tree):
        return etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)

    blobs["word/comments.xml"]         = ser(com_t)
    blobs["word/commentsExtended.xml"] = ser(cex_t)
    blobs["word/commentsIds.xml"]      = ser(cid_t)

    with zipfile.ZipFile(DOCX, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.writestr(n, blobs[n])
    TEMP.unlink(missing_ok=True)

    print(f"\nBacked up to: {BACKUP.name}")
    print(f"Applied {len(EDITS) + len(dynamic_edits)} single-run edits, {len(SPAN_EDITS)} span edit(s), "
          f"{len(COMMENTS)} comments. Saved: {DOCX.name}")


if __name__ == "__main__":
    main()
