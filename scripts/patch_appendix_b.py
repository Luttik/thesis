# -*- coding: utf-8 -*-
"""
Appendix B improvements: tracked changes for high-confidence fixes, comments
for the two bigger judgment calls (heading rename, section restructure) and
the content-completeness suggestions. Author "Claude".

Edits:
  413  "five stages ... auditing ... steering ... mediating the flow" ->
       "four stages ... navigating ... obtaining the resulting value outcomes"
       (matches the actual 4 headings below)                              + comment
  418  "Stay wary of the fact that" -> "Stay wary:"                       (tighten)
  419  missing trailing period
  425  "whilst staying without violating" -> "without violating"         (garbled phrase)
  429  "fall to" -> "fall into" (idiom) + comma splice -> semicolon
  437  heading "Mediating" -> "Obtaining" (matches Ch1/4/5/6/ExecSummary) + comment
  439  restores the missing 3rd risk category (security/privacy) + fixes
       repetition/stray comma
  440  "usecases" -> "use cases" (typo) + comma splice -> semicolon

Comments only (no text change):
  420  Navigating section: suggest 3-way sub-grouping (matches Ch4.2), flag
       item 427 as redundant with several others
  436  use-case guidance imbalance: only customer-facing gets a dedicated item
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
BACKUP = ROOT / "Thesis Draft - Daan Luttik - MBA.appendixB-backup.docx"

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


def clone_rpr(r):
    rpr = r.find(qn("w:rPr"))
    return copy.deepcopy(rpr) if rpr is not None else None


def _used_ids(doc):
    return {int(el.get(qn("w:id"), 0)) for el in doc.element.body.iter() if el.get(qn("w:id")) is not None}


def _nid(used):
    n = max(used, default=0) + 1
    used.add(n)
    return n


def mk_plain(text, rpr):
    r = etree.Element(qn("w:r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, qn("w:t")); t.set(XMLSPACE, "preserve"); t.text = text
    return r


def mk_del(text, rpr, used):
    d = etree.Element(qn("w:del"))
    d.set(qn("w:id"), str(_nid(used))); d.set(qn("w:author"), AUTHOR); d.set(qn("w:date"), DATE)
    r = etree.SubElement(d, qn("w:r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    dt = etree.SubElement(r, qn("w:delText")); dt.set(XMLSPACE, "preserve"); dt.text = text
    return d


def mk_ins(text, rpr, used):
    ins = etree.Element(qn("w:ins"))
    ins.set(qn("w:id"), str(_nid(used))); ins.set(qn("w:author"), AUTHOR); ins.set(qn("w:date"), DATE)
    r = etree.SubElement(ins, qn("w:r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, qn("w:t")); t.set(XMLSPACE, "preserve"); t.text = text
    return ins


def replace_text_tracked(p_elem, old, new, used) -> bool:
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
            parts.append(mk_plain(before, rpr))
        parts.append(mk_del(old, rpr, used))
        if new:
            parts.append(mk_ins(new, rpr, used))
        if after:
            parts.append(mk_plain(after, rpr))
        for j, part in enumerate(parts):
            parent.insert(idx + j, part)
        parent.remove(r)
        return True
    return False


def crs(cid):
    e = etree.Element(w("commentRangeStart")); e.set(w("id"), str(cid)); return e

def cre(cid):
    e = etree.Element(w("commentRangeEnd")); e.set(w("id"), str(cid)); return e

def cref(cid):
    r = etree.Element(w("r"))
    etree.SubElement(etree.SubElement(r, w("rPr")), w("rStyle")).set(w("val"), "CommentReference")
    etree.SubElement(r, w("commentReference")).set(w("id"), str(cid))
    return r


def comment_on_plain_substr(p_elem, substr, cid) -> bool:
    for r in p_elem.findall(w("r")):
        t = r.find(w("t"))
        if t is None or not t.text or substr not in t.text:
            continue
        rpr = clone_rpr(r)
        before, _, after = t.text.partition(substr)
        parent = r.getparent()
        idx = list(parent).index(r)
        seq = []
        if before:
            seq.append(mk_plain(before, rpr))
        seq += [crs(cid), mk_plain(substr, rpr), cre(cid), cref(cid)]
        if after:
            seq.append(mk_plain(after, rpr))
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


EDITS = [
    (413, "five stages", "four stages"),
    (413, "auditing the organizational conditions, steering the organization,",
          "navigating the organizational conditions,"),
    (413, "mediating the flow through to value outcomes", "obtaining the resulting value outcomes"),
    (418, "Stay wary of the fact that what you hear or read", "Stay wary: what you hear or read"),
    (419, "stories ", "stories."),
    (425, "whilst staying without violating", "without violating"),
    (429, "fall to analysis", "fall into analysis"),
    (429, "paralysis, try to find", "paralysis; try to find"),
    (437, "Mediating", "Obtaining"),
    (439, " like brand risk, and the risk of hallucinations.",
          ", including brand risk, security and privacy violations, and hallucinations."),
    (440, ", do not overdo it", "; do not overdo it"),
    (440, "small usecases", "small use cases"),
]

T_INTRO = ("Updated to match the structure below: the original said 'five stages' but only four headings "
           "exist (Observing / Navigating / Applying / [Mediating or Obtaining] Value Outcomes) -- "
           "'auditing the organizational conditions' and 'steering the organization' read like they were "
           "meant to be separate stages but got merged into one Navigating section without updating this "
           "sentence. Also changed the ending to 'obtaining the resulting value outcomes' to match the term "
           "used everywhere else (Ch1, Ch4.4, Ch5, Ch6, Executive Summary) -- see the paired rename on the "
           "heading below. Revert both if 'mediating' was a deliberate, more specific choice for this appendix.")
T_HEADING = ("Renamed to match the term used everywhere else in the thesis ('obtaining value outcomes' -- "
             "Ch1, Ch4.4, Ch5, Ch6, Executive Summary). Paired with the intro-paragraph edit above.")
T_NAVIGATING = ("This section has 11 items vs. 4-5 in every other section, and they're currently interleaved "
                "rather than grouped. Ch4.2 already splits this stage into three sub-themes: steering the "
                "marketing department (AI literacy, leadership backing, champions, bringing people along), "
                "leveraging technical resources (data/infrastructure/talent, agencies), and dealing with "
                "compliance (governance/GDPR/laboratory). Suggest breaking this section into three labeled "
                "sub-groups to match -- didn't do the reorder directly since moving many bullets is hard to "
                "review as a clean tracked change. Separately: 'Steer what you control: educate, run "
                "experiments, bring people along, provide clarity, and champion the work' restates five of "
                "the other bullets in condensed form -- could be dropped once sub-grouping makes those "
                "connections visible, or kept as a short intro line for the steering sub-group.")
T_USECASE_GAP = ("This is the only use case in 4.3 that gets a dedicated, specific checklist item -- "
                  "analytics/insights, content creation, and generic agents only appear in the parenthetical "
                  "list in the item above. Ch4.3 has specific findings for each (e.g. data connectivity for "
                  "analytics per interviewees 3/4/15; validation/governance scaffolding for content per "
                  "interviewees 6/9/11/16). Could add a parallel one-line item for each -- didn't draft new "
                  "content here since that's more of an authorial call than a copyedit. Say the word and "
                  "I'll draft them.")

COMMENTS = [
    (413, "value-creation model developed in Chapter 4", T_INTRO),
    (437, "Value Outcomes: turning application into value", T_HEADING),
    (420, "Navigating", T_NAVIGATING),
    (436, "For customer-facing agents", T_USECASE_GAP),
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

    reserved = [(next_cid + i, fresh_paraid(0x0C400001 + i), "%08X" % (max_dur + 1 + i))
                for i in range(len(COMMENTS))]

    doc = Document(str(DOCX))
    paras = doc.paragraphs
    used = _used_ids(doc)

    print("=== edits ===")
    failures = []
    for idx, old, new in EDITS:
        ok = replace_text_tracked(paras[idx]._element, old, new, used)
        print(f"[{'OK ' if ok else 'MISS'}] para {idx}: {old!r} -> {new!r}")
        if not ok:
            failures.append((idx, old))

    print("\n=== comments ===")
    for (idx, arg, _), (cid, paraid, durable) in zip(COMMENTS, reserved):
        ok = comment_on_plain_substr(paras[idx]._element, arg, cid)
        print(f"[{'OK ' if ok else 'MISS'}] comment {cid} -> para {idx}: {arg!r}")
        if not ok:
            failures.append((idx, arg))

    if failures:
        print(f"\nABORT: {len(failures)} failure(s); NOT saving.")
        return

    shutil.copy(DOCX, BACKUP)
    TEMP = ROOT / "Thesis Draft - Daan Luttik - MBA.appendixB-tmp.docx"
    doc.save(str(TEMP))

    with zipfile.ZipFile(TEMP) as z:
        names = z.namelist()
        blobs = {n: z.read(n) for n in names}

    com_t = etree.fromstring(blobs["word/comments.xml"])
    cex_t = etree.fromstring(blobs["word/commentsExtended.xml"])
    cid_t = etree.fromstring(blobs["word/commentsIds.xml"])

    for (_, _, text), (cid, paraid, durable) in zip(COMMENTS, reserved):
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
    print(f"Applied {len(EDITS)} edits, {len(COMMENTS)} comments. Saved: {DOCX.name}")


if __name__ == "__main__":
    main()
