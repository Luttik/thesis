# -*- coding: utf-8 -*-
"""Inject the supervisor's comments that are missing from the working doc.

Copies each missing <w:comment> (and its commentsExtended/Ids/Extensible
entries) from the SBcomments docx into the working docx with a fresh comment id,
and anchors it to the matching paragraph (whole-paragraph anchor for robustness).
Reports any comment whose anchor paragraph could not be located. Repackages the
docx directly (preserves all other parts byte-for-byte)."""
import zipfile, os, re, copy, shutil
from lxml import etree

BASE = r"C:\workspace\thesis"
WORK = os.path.join(BASE, "Thesis Draft - Daan Luttik - MBA - copy from 2026-06-13.docx")
SB = os.path.join(BASE, "NEW - Thesis Draft - Daan Luttik - MBA - SBcomments.docx")
OUT = WORK  # in place (backup already made)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
def w(t): return f"{{{W}}}{t}"

def load(part, z): return etree.fromstring(z.read(part))
def ctext(p): return "".join(t.text or "" for t in p.iter(w("t")))

# ---------- read SB ----------
zsb = zipfile.ZipFile(SB)
sb_comments = load("word/comments.xml", zsb)
sb_ext = load("word/commentsExtended.xml", zsb)
sb_ids = load("word/commentsIds.xml", zsb)
sb_cex = load("word/commentsExtensible.xml", zsb)
sb_doc = load("word/document.xml", zsb)

# comment elements by id
sb_cmt = {c.get(w("id")): c for c in sb_comments}
# paraId for each comment (first body para)
def para_id(cmt):
    p = cmt.find(w("p"))
    return p.get("{http://schemas.microsoft.com/office/word/2010/wordml}paraId") if p is not None else None
sb_cmt_para = {cid: para_id(c) for cid, c in sb_cmt.items()}
# ext/ids/cex by key
W15 = "http://schemas.microsoft.com/office/word/2012/wordml"
W16CID = "http://schemas.microsoft.com/office/word/2016/wordml/cid"
W16CEX = "http://schemas.microsoft.com/office/word/2018/wordml/cex"
ext_by_para = {e.get(f"{{{W15}}}paraId"): e for e in sb_ext}
ids_by_para = {e.get(f"{{{W16CID}}}paraId"): e for e in sb_ids}
durable_by_para = {pa: e.get(f"{{{W16CID}}}durableId") for pa, e in ids_by_para.items()}
cex_by_durable = {e.get(f"{{{W16CEX}}}durableId"): e for e in sb_cex}

# anchored text + containing-paragraph text for each comment id (walk SB document)
anchor_text = {}; para_key = {}
active = {}
for el in sb_doc.find(w("body")).iter():
    tag = etree.QName(el).localname
    if tag == "commentRangeStart":
        cid = el.get(w("id")); active[cid] = True; anchor_text.setdefault(cid, "")
    elif tag == "commentRangeEnd":
        active.pop(el.get(w("id")), None)
    elif tag == "t":
        for cid in active: anchor_text[cid] += (el.text or "")
# containing paragraph = the paragraph that holds each comment's commentRangeStart
for p in sb_doc.find(w("body")).iter(w("p")):
    for crs in p.iter(w("commentRangeStart")):
        para_key.setdefault(crs.get(w("id")), ctext(p))

# comment body text for matching
def body_text(c): return " ".join(ctext(p) for p in c.findall(w("p"))).strip()
sb_text = {cid: body_text(c) for cid, c in sb_cmt.items()}

# ---------- read WORKING ----------
zwk = zipfile.ZipFile(WORK)
wk_comments = load("word/comments.xml", zwk)
wk_ext = load("word/commentsExtended.xml", zwk)
wk_ids = load("word/commentsIds.xml", zwk)
wk_cex = load("word/commentsExtensible.xml", zwk)
wk_doc = load("word/document.xml", zwk)
wk_body = wk_doc.find(w("body"))

def norm(t): return re.sub(r"\s+", " ", t).strip().lower()[:80]
wk_text_set = set(norm(body_text(c)) for c in wk_comments)
max_id = max(int(c.get(w("id"))) for c in wk_comments)

# missing comment ids (supervisor + others), preserve SB order
missing = [cid for cid in sb_cmt if norm(sb_text[cid]) not in wk_text_set]

# working paragraphs raw text (w:t only)
wk_paras = [(p, ctext(p)) for p in wk_body.iter(w("p")) if p.getparent().tag == w("body")]

# manual re-anchors for comments whose original target was restructured by our edits
OVERRIDES = {
    "135": "Figure 1 presents the resulting process model",       # rewrite-to-describe-Figure-1
    "137": "Figure 1 presents the resulting process model",       # "studied managers experienced"
    "247": "Taken together, the benefits, sacrifices, and risks above describe",  # integrate the table
}

def find_para(sb_par_text):
    """Return (paragraph, quality) where quality is 'exact' (unique) or 'approx'
    (first match on a shorter key), else (None, None)."""
    s = re.sub(r"\s+", " ", sb_par_text).strip()
    if not s: return None, None
    norm_paras = [(p, re.sub(r"\s+", " ", txt)) for p, txt in wk_paras]
    for klen in (45, 30):
        for a in range(0, max(1, len(s) - klen + 1), 15):
            key = s[a:a + klen]
            if len(key) < 25: continue
            hits = [p for p, txt in norm_paras if key in txt]
            if len(hits) == 1:
                return hits[0], "exact"
    for klen in (25,):  # lenient: accept first match
        for a in range(0, max(1, len(s) - klen + 1), 12):
            key = s[a:a + klen]
            if len(key) < 22: continue
            hits = [p for p, txt in norm_paras if key in txt]
            if hits:
                return hits[0], "approx"
    return None, None

def find_by_marker(marker):
    for p, txt in wk_paras:
        if marker in txt: return p
    return None

def anchor_para(p, cid):
    pPr = p.find(w("pPr"))
    idx = (list(p).index(pPr) + 1) if pPr is not None else 0
    crs = etree.Element(w("commentRangeStart")); crs.set(w("id"), str(cid))
    p.insert(idx, crs)
    cre = etree.Element(w("commentRangeEnd")); cre.set(w("id"), str(cid))
    p.append(cre)
    r = etree.SubElement(p, w("r"))
    rPr = etree.SubElement(r, w("rPr")); rs = etree.SubElement(rPr, w("rStyle")); rs.set(w("val"), "CommentReference")
    cr = etree.SubElement(r, w("commentReference")); cr.set(w("id"), str(cid))

results = []
next_id = max_id + 1
for cid in missing:
    if cid in OVERRIDES:
        target = find_by_marker(OVERRIDES[cid]); quality = "override"
    else:
        sb_par = para_key.get(cid, "")
        target, quality = find_para(sb_par) if sb_par else (None, None)
    if target is None:
        results.append(("FAIL", cid, sb_text[cid][:55])); continue
    new_id = str(next_id); next_id += 1
    # copy comment element
    nc = copy.deepcopy(sb_cmt[cid]); nc.set(w("id"), new_id)
    wk_comments.append(nc)
    pa = sb_cmt_para[cid]
    if pa in ext_by_para: wk_ext.append(copy.deepcopy(ext_by_para[pa]))
    if pa in ids_by_para: wk_ids.append(copy.deepcopy(ids_by_para[pa]))
    dur = durable_by_para.get(pa)
    if dur in cex_by_durable: wk_cex.append(copy.deepcopy(cex_by_durable[dur]))
    anchor_para(target, new_id)
    results.append((quality.upper(), cid, f"#{new_id} -> {sb_text[cid][:45]}"))

# ---------- repackage ----------
zwk.close(); zsb.close()
mods = {
    "word/comments.xml": etree.tostring(wk_comments, xml_declaration=True, encoding="UTF-8", standalone=True),
    "word/commentsExtended.xml": etree.tostring(wk_ext, xml_declaration=True, encoding="UTF-8", standalone=True),
    "word/commentsIds.xml": etree.tostring(wk_ids, xml_declaration=True, encoding="UTF-8", standalone=True),
    "word/commentsExtensible.xml": etree.tostring(wk_cex, xml_declaration=True, encoding="UTF-8", standalone=True),
    "word/document.xml": etree.tostring(wk_doc, xml_declaration=True, encoding="UTF-8", standalone=True),
}
src = zipfile.ZipFile(WORK)
tmp = OUT + ".new"
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in src.infolist():
        data = mods.get(item.filename, src.read(item.filename))
        zout.writestr(item, data)
src.close()
os.replace(tmp, OUT)

ok = [r for r in results if r[0] != "FAIL"]; fail = [r for r in results if r[0] == "FAIL"]
from collections import Counter
print(f"Injected {len(ok)} / {len(missing)} missing comments. New ids {max_id+1}..{next_id-1}")
print("quality:", dict(Counter(r[0] for r in ok)))
print("\nAPPROX anchors (landed in right area, maybe not exact paragraph):")
for q, cid, t in ok:
    if q == "APPROX": print(f"  {t}")
print("\nFAILED to anchor (left out — text changed too much):")
for _, cid, t in fail: print(f"  SB#{cid}: {t}")
