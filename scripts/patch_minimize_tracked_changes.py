# -*- coding: utf-8 -*-
"""
Shrink existing Claude-authored tracked changes down to their minimal diff.

Problem: every prior patch script tracked the whole matched substring as
deleted+inserted, even when old/new shared a common prefix/suffix -- e.g.
"will be collected and converted" -> "were collected and converted" tracked
"collected and converted" as both struck-through AND re-inserted, though it
never changed. This walks the CURRENT live XML (not the old edit scripts --
one prior pass isn't in this session's script history) and, for every
directly-adjacent Claude <w:del> immediately followed by Claude <w:ins>,
trims the shared leading/trailing word-tokens back out to plain (untouched)
runs, leaving only the true differing middle wrapped in del/ins.

Only touches PAIRS where del is immediately followed by ins with nothing
(no comment marker, nothing) in between -- by construction that means no
comment range can be interspersed, so this never disturbs a comment anchor
that sits before the del or after the ins (those markers simply stay put
relative to the, possibly now-larger-in-element-count, replacement).

One exception found by inspection and deliberately skipped: para 122's
"During data gathering we" -> "the researcher" has a comment wrapping
specifically the <w:ins>, not directly adjacent to the del (a comment
range sits between them) -- left untouched (also, only a 1-char trailing
space would be reclaimed there, not worth the structural risk).

One extra hand-handled case: para 299's double-space fix was produced by
replace_span_tracked's multi-run branch, which for a non-empty `new` emits
ins-before-del (opposite order from replace_text_tracked's del-before-ins),
so it wasn't caught by the main del->ins scan. Handled explicitly below by
its exact, unambiguous text signature.
"""
from __future__ import annotations

import copy
import re
import shutil
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from lxml import etree

ROOT   = Path(__file__).resolve().parents[1]
DOCX   = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP = ROOT / "Thesis Draft - Daan Luttik - MBA.pre-minimize-backup.docx"

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"


def w(t): return f"{{{W}}}{t}"


def tokenize(s: str) -> list[str]:
    return re.findall(r"\w+|.", s, re.DOTALL)


def minimal_diff(old_text: str, new_text: str, allow_suffix: bool = True):
    old_tok, new_tok = tokenize(old_text), tokenize(new_text)
    i = 0
    while i < len(old_tok) and i < len(new_tok) and old_tok[i] == new_tok[i]:
        i += 1
    j = 0
    if allow_suffix:
        max_suffix = min(len(old_tok) - i, len(new_tok) - i)
        while j < max_suffix and old_tok[len(old_tok) - 1 - j] == new_tok[len(new_tok) - 1 - j]:
            j += 1
    prefix = "".join(old_tok[:i])
    old_mid = "".join(old_tok[i:len(old_tok) - j]) if j else "".join(old_tok[i:])
    new_mid = "".join(new_tok[i:len(new_tok) - j]) if j else "".join(new_tok[i:])
    suffix = "".join(old_tok[len(old_tok) - j:]) if j else ""
    return prefix, old_mid, new_mid, suffix


def clone_rpr(el):
    rpr = el.find(qn("w:rPr"))
    return copy.deepcopy(rpr) if rpr is not None else None


def _used_ids(doc) -> set[int]:
    return {int(el.get(qn("w:id"), 0)) for el in doc.element.body.iter() if el.get(qn("w:id")) is not None}


def _nid(used: set[int]) -> int:
    n = max(used, default=0) + 1
    used.add(n)
    return n


def mk_plain(text, rpr):
    r = etree.Element(qn("w:r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, qn("w:t")); t.set(XMLSPACE, "preserve"); t.text = text
    return r


def mk_del(text, rpr, author, date, used):
    d = etree.Element(qn("w:del"))
    d.set(qn("w:id"), str(_nid(used))); d.set(qn("w:author"), author); d.set(qn("w:date"), date)
    r = etree.SubElement(d, qn("w:r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    dt = etree.SubElement(r, qn("w:delText")); dt.set(XMLSPACE, "preserve"); dt.text = text
    return d


def mk_ins(text, rpr, author, date, used):
    ins = etree.Element(qn("w:ins"))
    ins.set(qn("w:id"), str(_nid(used))); ins.set(qn("w:author"), author); ins.set(qn("w:date"), date)
    r = etree.SubElement(ins, qn("w:r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, qn("w:t")); t.set(XMLSPACE, "preserve"); t.text = text
    return ins


def txt_del(el): return "".join(t.text or "" for t in el.iter(w("delText")))
def txt_ins(el): return "".join(t.text or "" for t in el.iter(w("t")))


def main():
    doc = Document(str(DOCX))
    body = doc.element.body
    used = _used_ids(doc)

    n_pairs = n_reduced = n_chars_saved = 0

    for p in body.iter(w("p")):
        children = list(p)
        i = 0
        while i < len(children):
            el = children[i]
            if (etree.QName(el).localname == "del" and el.get(w("author")) == "Claude"
                    and i + 1 < len(children)):
                nxt = children[i + 1]
                if etree.QName(nxt).localname == "ins" and nxt.get(w("author")) == "Claude":
                    n_pairs += 1
                    del_el, ins_el = el, nxt
                    old_text, new_text = txt_del(del_el), txt_ins(ins_el)
                    after = children[i + 2] if i + 2 < len(children) else None
                    after_tag = etree.QName(after).localname if after is not None else None
                    allow_suffix = after_tag not in ("commentRangeEnd", "commentReference")
                    prefix, old_mid, new_mid, suffix = minimal_diff(old_text, new_text, allow_suffix)
                    if prefix or suffix:
                        n_reduced += 1
                        n_chars_saved += len(prefix) + len(suffix)
                        del_rpr, ins_rpr = clone_rpr(del_el.find(w("r"))), clone_rpr(ins_el.find(w("r")))
                        author = del_el.get(w("author"))
                        date = del_el.get(w("date"))
                        ins_date = ins_el.get(w("date"))
                        replacement = []
                        if prefix:
                            replacement.append(mk_plain(prefix, del_rpr))
                        if old_mid:
                            replacement.append(mk_del(old_mid, del_rpr, author, date, used))
                        if new_mid:
                            replacement.append(mk_ins(new_mid, ins_rpr, author, ins_date, used))
                        if suffix:
                            replacement.append(mk_plain(suffix, ins_rpr))
                        parent = del_el.getparent()
                        idx = list(parent).index(del_el)
                        parent.remove(del_el)
                        parent.remove(ins_el)
                        for k, node in enumerate(replacement):
                            parent.insert(idx + k, node)
                        children = list(p)  # refresh after mutation
                        i = idx + len(replacement)
                        continue
            i += 1

    print(f"del->ins pairs found: {n_pairs}, reduced: {n_reduced}, "
          f"chars moved from tracked to plain: {n_chars_saved}")

    # --- special case: double-space fix produced as ins(' ') then del('  ') or del(' ')del(' ') ---
    special_hits = 0
    for p in body.iter(w("p")):
        children = list(p)
        for i, el in enumerate(children):
            if etree.QName(el).localname == "ins" and el.get(w("author")) == "Claude" and txt_ins(el) == " ":
                d1 = children[i + 1] if i + 1 < len(children) else None
                if d1 is None or etree.QName(d1).localname != "del" or d1.get(w("author")) != "Claude":
                    continue
                d1_text = txt_del(d1)
                consumed = [d1]
                if d1_text == "  ":
                    pass  # single merged del already has both spaces
                elif d1_text == " ":
                    d2 = children[i + 2] if i + 2 < len(children) else None
                    if (d2 is not None and etree.QName(d2).localname == "del"
                            and d2.get(w("author")) == "Claude" and txt_del(d2) == " "):
                        consumed.append(d2)
                    else:
                        continue
                else:
                    continue
                special_hits += 1
                rpr = clone_rpr(d1.find(w("r")))
                author, date = d1.get(w("author")), d1.get(w("date"))
                plain = mk_plain(" ", rpr)
                new_del = mk_del(" ", rpr, author, date, used)
                parent = el.getparent()
                idx = list(parent).index(el)
                parent.remove(el)
                for d in consumed:
                    parent.remove(d)
                parent.insert(idx, plain)
                parent.insert(idx + 1, new_del)
    print(f"special-cased ins+del double-space fixes: {special_hits}")

    shutil.copy(DOCX, BACKUP)
    doc.save(str(DOCX))
    print(f"\nBacked up to: {BACKUP.name}\nSaved: {DOCX.name}")


if __name__ == "__main__":
    main()
