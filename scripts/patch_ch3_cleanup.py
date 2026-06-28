# -*- coding: utf-8 -*-
"""
Chapter 3 cleanup:
  1. Tracked DELETION of the illogical hypothetical sentence in 3.1 (113):
     "Throughout the research process, sensitizing concepts might be added or
      disregarded to fit the emerging concepts (Charmaz, 2014)."
  2. Two new review comments flagging statements repeated within a short range
     (3.2 -> 3.3): theoretical saturation (119 & 123) and theoretical sampling
     (119 & 123, the latter opening "As noted before").

Operates directly on the docx zip (document.xml + the four comment parts),
appending to the existing 248-id comment space and 22 tracked changes.
"""
from __future__ import annotations

import copy
import shutil
import zipfile
from pathlib import Path

from lxml import etree

ROOT   = Path(__file__).resolve().parents[1]
DOCX   = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP = ROOT / "Thesis Draft - Daan Luttik - MBA.ch3-cleanup-backup.docx"

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

DEL_MARKER  = "Throughout the research process"          # start of sentence to delete (in 113)
DEL_PARA_ID = "sensitizing concepts might be added or disregarded"  # locates 113
DEL_TAIL    = "(Charmaz, 2014)."                          # citation runs to fully delete

T_SATURATION = ("Repeated: theoretical saturation is already defined in 3.2 ('After reaching theoretical "
                "saturation, the point where new data no longer yields new insights'). Consider defining it "
                "once and here simply stating that data gathering stopped at saturation.")
T_SAMPLING  = ("Repeated: theoretical sampling is already explained in 3.2 ('theoretical sampling was applied, "
               "i.e., instead of sampling for population representativeness, specific data is sought to elaborate "
               "and refine the properties of their emerging categories'). The opening 'As noted before' confirms "
               "the repetition; consider consolidating into one place.")


# --------------------------------------------------------------------------- #
def para_text(p):
    return "".join(t.text or "" for t in p.iter(w("t")))

def find_para(body, substr):
    for p in body.iter(w("p")):
        if substr in para_text(p):
            return p
    return None

def direct_runs(p):
    return [r for r in p if r.tag == w("r")]

def clone_rpr(r):
    rpr = r.find(w("rPr"))
    return copy.deepcopy(rpr) if rpr is not None else None

def nid(used):
    n = max(used, default=0) + 1
    used.add(n)
    return n


def mk_run(text, rpr):
    r = etree.Element(w("r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, w("t")); t.set(XMLSPACE, "preserve"); t.text = text
    return r

def mk_del(text, rpr, used):
    d = etree.Element(w("del"))
    d.set(w("id"), str(nid(used))); d.set(w("author"), AUTHOR); d.set(w("date"), DATE)
    r = etree.SubElement(d, w("r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    dt = etree.SubElement(r, w("delText")); dt.set(XMLSPACE, "preserve"); dt.text = text
    return d

def del_whole_run(r, used):
    r.getparent().replace(r, mk_del(r.find(w("t")).text or "", clone_rpr(r), used))

def del_tail(r, keep_prefix, used):
    rpr = clone_rpr(r); full = r.find(w("t")).text
    remainder = full[len(keep_prefix):]
    parent = r.getparent(); idx = list(parent).index(r)
    parent.insert(idx, mk_run(keep_prefix, rpr))
    parent.insert(idx + 1, mk_del(remainder, rpr, used))
    parent.remove(r)


def crs(cid):
    e = etree.Element(w("commentRangeStart")); e.set(w("id"), str(cid)); return e

def cre(cid):
    e = etree.Element(w("commentRangeEnd")); e.set(w("id"), str(cid)); return e

def cref(cid):
    r = etree.Element(w("r"))
    etree.SubElement(etree.SubElement(r, w("rPr")), w("rStyle")).set(w("val"), "CommentReference")
    etree.SubElement(r, w("commentReference")).set(w("id"), str(cid))
    return r

def comment_substr(para, substr, cid):
    """Highlight exactly `substr` inside its host plain run and attach comment cid."""
    for r in direct_runs(para):
        t = r.find(w("t"))
        if t is None or not t.text or substr not in t.text:
            continue
        rpr = clone_rpr(r); before, _, after = t.text.partition(substr)
        parent = para; idx = list(parent).index(r)
        seq = []
        if before:
            seq.append(mk_run(before, rpr))
        seq += [crs(cid), mk_run(substr, rpr), cre(cid), cref(cid)]
        if after:
            seq.append(mk_run(after, rpr))
        for j, el in enumerate(seq):
            parent.insert(idx + j, el)
        parent.remove(r)
        return True
    return False


def add_comment(com_t, cex_t, cid_t, cid, paraid, durable, text):
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


def main():
    with zipfile.ZipFile(DOCX) as z:
        names = z.namelist()
        blobs = {n: z.read(n) for n in names}

    body  = etree.fromstring(blobs["word/document.xml"])
    com_t = etree.fromstring(blobs["word/comments.xml"])
    cex_t = etree.fromstring(blobs["word/commentsExtended.xml"])
    cid_t = etree.fromstring(blobs["word/commentsIds.xml"])

    # ---- pre-allocate ids (avoid collisions across revisions + comment ranges) ----
    doc_ids = {int(e.get(w("id"))) for e in body.iter() if e.get(w("id")) is not None}
    com_ids = {int(c.get(w("id"))) for c in com_t.findall(w("comment"))}
    cid_sat, cid_samp = max(com_ids) + 1, max(com_ids) + 2
    used = doc_ids | {cid_sat, cid_samp}                       # del-revision ids start above these
    used_paraids = {p.get(w14("paraId"), "").upper() for c in com_t.findall(w("comment")) for p in c.iter(w("p"))}
    max_dur = max(int(x.get(w16("durableId")), 16) for x in cid_t)

    # ---- 1. tracked deletion in 113 ----
    p113 = find_para(body, DEL_PARA_ID)
    assert p113 is not None, "para 113 not found"
    runs = direct_runs(p113)
    r_marker = next((r for r in runs if (r.find(w("t")) is not None and r.find(w("t")).text and DEL_MARKER in r.find(w("t")).text)), None)
    assert r_marker is not None, "deletion marker run not found"
    full = r_marker.find(w("t")).text
    cut = full.index(DEL_MARKER)
    while cut > 0 and full[cut - 1] == " ":
        cut -= 1
    keep_prefix = full[:cut]
    tail = runs[runs.index(r_marker) + 1:]
    tail_text = "".join((r.find(w("t")).text or "") for r in tail if r.find(w("t")) is not None)
    assert tail_text == DEL_TAIL, f"unexpected tail to delete: {tail_text!r}"
    del_tail(r_marker, keep_prefix, used)
    for r in tail:
        del_whole_run(r, used)
    print(f"[OK] deleted 113 sentence; kept prefix ends: ...{keep_prefix[-40:]!r}")

    # ---- 2. redundancy comments in 123 ----
    p123 = find_para(body, "data gathering stopped when")
    assert p123 is not None, "para 123 not found"
    ok1 = comment_substr(p123, "In line with the concept of theoretical saturation", cid_sat)
    ok2 = comment_substr(
        p123,
        "data gathering was steered by theoretical sampling, which relies on the circular process of "
        "administering interviews, writing memos, and coding data into relevant categories",
        cid_samp,
    )
    assert ok1 and ok2, f"comment anchors not found (sat={ok1}, samp={ok2})"
    add_comment(com_t, cex_t, cid_t, cid_sat,  "0C1A0006", "%08X" % (max_dur + 1), T_SATURATION)
    add_comment(com_t, cex_t, cid_t, cid_samp, "0C1A0007", "%08X" % (max_dur + 2), T_SAMPLING)
    print(f"[OK] comment {cid_sat} (saturation) + {cid_samp} (sampling) anchored in 123")

    def ser(tree):
        return etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)

    blobs["word/document.xml"]         = ser(body)
    blobs["word/comments.xml"]         = ser(com_t)
    blobs["word/commentsExtended.xml"] = ser(cex_t)
    blobs["word/commentsIds.xml"]      = ser(cid_t)

    shutil.copy(DOCX, BACKUP)
    with zipfile.ZipFile(DOCX, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.writestr(n, blobs[n])
    print(f"\nBacked up to: {BACKUP.name}\nSaved: {DOCX.name}")


if __name__ == "__main__":
    main()
