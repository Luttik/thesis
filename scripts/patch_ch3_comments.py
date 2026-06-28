# -*- coding: utf-8 -*-
"""
Add 5 Word review comments to Chapter 3 at the spots that need a human decision
(not the mechanical tense flips). Appends to the doc's existing comment parts
(188 comments already present) with non-colliding ids, and anchors each comment
to the relevant run(s) in document.xml.

Single pass over the docx zip: parse document.xml + comments.xml +
commentsExtended.xml + commentsIds.xml, insert commentRangeStart/End +
commentReference markers, append <w:comment>/<w15:commentEx>/<w16cid:commentId>,
then rewrite the zip.
"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from lxml import etree

ROOT   = Path(__file__).resolve().parents[1]
DOCX   = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP = ROOT / "Thesis Draft - Daan Luttik - MBA.ch3-comments-backup.docx"

W   = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
W15 = "http://schemas.microsoft.com/office/word/2012/wordml"
W16 = "http://schemas.microsoft.com/office/word/2016/wordml/cid"
XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"


def w(t):   return f"{{{W}}}{t}"
def w14(t): return f"{{{W14}}}{t}"
def w15(t): return f"{{{W15}}}{t}"
def w16(t): return f"{{{W16}}}{t}"


AUTHOR, INITIALS, DATE = "Claude", "C", "2026-06-23T00:00:00Z"

# Comment text (plain ASCII; house style: no em dashes).
T_GRAMMAR = ("'was used' (singular) agrees with the head noun 'notion'. If you mean the "
             "sensitizing concepts themselves (plural), use 'were used'. Confirm the intended reading.")
T_HEADING = ("Retitled from 'Intended sample and sample size'. The Table of Contents still shows the "
             "old title, update it in Word (right-click the TOC > Update Field) before submitting.")
T_CRITERIA = ("Left in present tense as a description of the selection criteria. For uniform past tense "
              "across 3.1-3.3, change to 'the focus was on those who had a clear managerial role...'.")
T_SAMPLING = ("Changed from 'purposive sampling (Patton, 2014)' to 'theoretical sampling (Charmaz, 2014)'. "
              "Please confirm. Caveat: this paragraph describes the initial, network-based recruitment, "
              "which in grounded theory is usually initial/purposive sampling; theoretical sampling "
              "(see 3.2 and the next paragraph) is what steered later recruitment. If your supervisor "
              "distinguishes the two, you may want to keep 'purposive' here. Patton (2014) was dropped "
              "because it covers purposive, not theoretical, sampling.")
T_REDUND = ("This repeats the previous sentence ('candidates were selected when their roles matched the "
            "selection criteria'). Consider deleting or merging.")


def find_ins_by_text(body, text):
    """Return the <w:ins> whose single <w:t> equals text exactly."""
    for ins in body.iter(w("ins")):
        ts = ins.findall(".//" + w("t"))
        if len(ts) == 1 and (ts[0].text or "") == text:
            return ins
    return None


def find_plain_runs(body, substr):
    """Return plain <w:r> (not inside ins/del) whose <w:t> contains substr."""
    out = []
    for r in body.iter(w("r")):
        a, inside = r.getparent(), False
        while a is not None:
            if a.tag in (w("ins"), w("del")):
                inside = True
                break
            a = a.getparent()
        if inside:
            continue
        t = r.find(w("t"))
        if t is not None and t.text and substr in t.text:
            out.append(r)
    return out


def crs(cid):
    e = etree.Element(w("commentRangeStart")); e.set(w("id"), str(cid)); return e

def cre(cid):
    e = etree.Element(w("commentRangeEnd")); e.set(w("id"), str(cid)); return e

def cref(cid):
    r = etree.Element(w("r"))
    rpr = etree.SubElement(r, w("rPr"))
    rs = etree.SubElement(rpr, w("rStyle")); rs.set(w("val"), "CommentReference")
    cr = etree.SubElement(r, w("commentReference")); cr.set(w("id"), str(cid))
    return r


def wrap(start_anchor, end_anchor, cid):
    """commentRangeStart before start_anchor; commentRangeEnd + reference after end_anchor."""
    pe = end_anchor.getparent(); i = list(pe).index(end_anchor)
    pe.insert(i + 1, cre(cid)); pe.insert(i + 2, cref(cid))
    ps = start_anchor.getparent(); j = list(ps).index(start_anchor)
    ps.insert(j, crs(cid))


def main():
    with zipfile.ZipFile(DOCX) as z:
        names = z.namelist()
        blobs = {n: z.read(n) for n in names}

    doc_t = etree.fromstring(blobs["word/document.xml"])
    com_t = etree.fromstring(blobs["word/comments.xml"])
    cex_t = etree.fromstring(blobs["word/commentsExtended.xml"])
    cid_t = etree.fromstring(blobs["word/commentsIds.xml"])

    # next ids
    next_id = max(int(c.get(w("id"))) for c in com_t.findall(w("comment"))) + 1
    used_paraids = {p.get(w14("paraId"), "").upper()
                    for c in com_t.findall(w("comment")) for p in c.iter(w("p"))}
    used_paraids |= {e.get(w15("paraId"), "").upper() for e in cex_t}
    max_dur = max(int(x.get(w16("durableId")), 16) for x in cid_t)

    def fresh_paraid(seed):
        v = seed
        while ("%08X" % v) in used_paraids:
            v += 1
        used_paraids.add("%08X" % v)
        return "%08X" % v

    # (label, kind, args, text) -- in document order so ids read top-to-bottom
    plan = [
        ("grammar (3.1, 113)",  "ins",  ("was used to spark",), T_GRAMMAR),
        ("heading (3.3, 120)",  "ins",  ("Sample and sample size",), T_HEADING),
        ("criteria (3.3, 121)", "run",  ("the focus is on",), T_CRITERIA),
        ("sampling (3.3, 122)", "span", ("theoretical ", "Charmaz, 2014"), T_SAMPLING),
        ("redundancy (3.3, 122)", "ins", ("Candidates were selected based on their role",), T_REDUND),
    ]

    # resolve all anchors first; abort if any missing
    resolved = []
    for label, kind, args, text in plan:
        if kind == "ins":
            a = find_ins_by_text(doc_t, args[0])
            assert a is not None, f"anchor not found (ins): {label} {args}"
            resolved.append((label, a, a, text))
        elif kind == "run":
            rs = find_plain_runs(doc_t, args[0])
            assert len(rs) == 1, f"anchor ambiguous/missing (run): {label} found {len(rs)}"
            resolved.append((label, rs[0], rs[0], text))
        elif kind == "span":
            s = find_ins_by_text(doc_t, args[0]); e = find_ins_by_text(doc_t, args[1])
            assert s is not None and e is not None, f"span anchors missing: {label}"
            assert s.getparent() is e.getparent(), f"span anchors in different paragraphs: {label}"
            resolved.append((label, s, e, text))

    # apply
    for i, (label, sa, ea, text) in enumerate(resolved):
        cid = next_id + i
        paraid = fresh_paraid(0x0C1A0001 + i)
        durable = "%08X" % (max_dur + 1 + i)
        wrap(sa, ea, cid)

        # comments.xml
        c = etree.SubElement(com_t, w("comment"))
        c.set(w("id"), str(cid)); c.set(w("author"), AUTHOR)
        c.set(w("date"), DATE); c.set(w("initials"), INITIALS)
        p = etree.SubElement(c, w("p"))
        p.set(w14("paraId"), paraid); p.set(w14("textId"), "77777777")
        pPr = etree.SubElement(p, w("pPr"))
        etree.SubElement(pPr, w("pStyle")).set(w("val"), "CommentText")
        r1 = etree.SubElement(p, w("r"))
        etree.SubElement(etree.SubElement(r1, w("rPr")), w("rStyle")).set(w("val"), "CommentReference")
        etree.SubElement(r1, w("annotationRef"))
        r2 = etree.SubElement(p, w("r"))
        t = etree.SubElement(r2, w("t")); t.set(XMLSPACE, "preserve"); t.text = text

        # commentsExtended.xml (done=0 -> shows as open/unresolved)
        ex = etree.SubElement(cex_t, w15("commentEx"))
        ex.set(w15("paraId"), paraid); ex.set(w15("done"), "0")

        # commentsIds.xml
        ci = etree.SubElement(cid_t, w16("commentId"))
        ci.set(w16("paraId"), paraid); ci.set(w16("durableId"), durable)

        print(f"[OK] comment {cid} -> {label}  (paraId {paraid})")

    def ser(tree):
        return etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)

    blobs["word/document.xml"]         = ser(doc_t)
    blobs["word/comments.xml"]         = ser(com_t)
    blobs["word/commentsExtended.xml"] = ser(cex_t)
    blobs["word/commentsIds.xml"]      = ser(cid_t)

    shutil.copy(DOCX, BACKUP)
    with zipfile.ZipFile(DOCX, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.writestr(n, blobs[n])

    print(f"\nBacked up to: {BACKUP.name}")
    print(f"Added {len(resolved)} comments (ids {next_id}-{next_id+len(resolved)-1}), saved: {DOCX.name}")


if __name__ == "__main__":
    main()
