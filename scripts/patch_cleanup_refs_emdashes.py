# -*- coding: utf-8 -*-
"""
(1) Remove 8 orphaned DC/DT references (tracked, author "Claude").
(2) Replace every em dash (U+2014) in the live body text with grammatically
    appropriate punctuation (comma / semicolon / colon / parentheses) — UNTRACKED
    direct text edits. Em dashes inside cited paper *titles* in the reference list
    are left verbatim.
"""
from __future__ import annotations
import shutil
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn

from patch_sec44_inside_out import _used_ids
from patch_sec23_dc_value import del_para_deep

ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP = ROOT / "Thesis Draft - Daan Luttik - MBA.cleanup-backup.docx"
EM = "—"

def anc_del(el, stop):
    p = el.getparent()
    while p is not None and p is not stop:
        if etree_local(p) == "del": return True
        p = p.getparent()
    return False
def etree_local(el):
    from lxml import etree
    return etree.QName(el).localname
def accept_text(p):
    return "".join(t.text or "" for t in p.iter(qn("w:t")) if not anc_del(t, p))
def find_p(body, anchor):
    for p in body.iter(qn("w:p")):
        if anchor in accept_text(p):
            return p
    return None

# ---- (1) references to remove (unique anchor substrings) ------------------- #
REMOVE = [
    "Profiting from technological innovation",                 # Teece 1986
    "Dynamic capabilities and strategic management. Strategic",# Teece 1997
    "Building dynamic capabilities for digital transformation",# Warner & Wäger 2019
    "Dynamic capabilities for digital transformation. Journal",# Ellström 2022
    "Unpacking the difference between digital transformation",  # Wessel 2021
    "Inside the successful make-up of",                         # Bughin 2024
    "Accountable acceleration",                                 # Wharton 2025
    "Value creation and value capture: A multilevel",          # Lepak 2007
]

# ---- (2) em-dash specs per paragraph (ordered by dash appearance) ---------- #
# spec tokens: comma ',', semi ';', colon ':', open '(', close ')'
EMDASH = [
    ("Transferability requires sufficient contextual detail", [","]),
    ("few organizations in the data have seen consumer-owned", [","]),
    ("a mediocre analyst that you still have to sense check", [","]),
    ("value with agentic AI is emergent from configuration-in-use", [":"]),
    ("three-part repertoire through which managers act", ["(", ")"]),
    ("recast the relationship between value creation and value destruction", [","]),
    ("The most consistent obstacle to value was organizational", [":", ",", "(", ")"]),
    ("Much adoption is essentially AI hygiene", ["(", ")"]),
    ("Value was most reliably created when managers began from", [":"]),
    ("Two resourcing decisions recur", [","]),
    ("Two interrelated limitations concern the scope", ["(", ")"]),
    ("Two further limitations deserve brief acknowledgement", ["(", ")"]),
    ("A more fundamental limitation is temporal", [",", ",", "(", ")"]),
    ("The study relies exclusively on interview data", [":", ",", "(", ")"]),
    ("The three subquestions structure this answer", ["(", ")"]),
    ("They enable adoption by steering the organization", [","]),
    ("Empirically, this study answers recent calls", ["(", ")"]),
    ("organizational lag", [","]),
]

def apply_specs(p, specs):
    di = 0
    for t in p.iter(qn("w:t")):
        if anc_del(t, p):
            continue
        s = t.text
        if not s or EM not in s:
            continue
        out, i = [], 0
        while i < len(s):
            c = s[i]
            if c == EM and di < len(specs):
                spec = specs[di]; di += 1
                before_sp = bool(out) and out[-1] == " "
                after_sp = (i + 1 < len(s) and s[i + 1] == " ")
                if spec in (",", ";", ":"):
                    if before_sp: out.pop()
                    out.append(spec)
                    if not after_sp: out.append(" ")
                    i += 1
                elif spec == "(":
                    out.append("(")
                    i += 2 if after_sp else 1
                elif spec == ")":
                    if before_sp: out.pop()
                    out.append(")")
                    i += 1
            else:
                out.append(c); i += 1
        t.text = "".join(out)
    return di

def main():
    shutil.copy(DOCX, BACKUP)
    doc = Document(str(DOCX))
    used = _used_ids(doc)
    body = doc.element.body

    # (1) remove refs
    removed = 0
    for anchor in REMOVE:
        el = find_p(body, anchor)
        assert el is not None, f"reference not found: {anchor!r}"
        del_para_deep(el, used); removed += 1
    print(f"(1) removed {removed} reference entries (tracked)")

    # (2) em dashes
    total = 0
    for anchor, specs in EMDASH:
        el = find_p(body, anchor)
        assert el is not None, f"em-dash paragraph not found: {anchor!r}"
        n = apply_specs(el, specs)
        assert n == len(specs), f"dash count mismatch in {anchor!r}: applied {n}, expected {len(specs)}"
        total += n
    print(f"(2) replaced {total} em dashes (untracked)")

    doc.save(str(DOCX))
    print(f"\nSaved: {DOCX}\nBackup: {BACKUP}")

if __name__ == "__main__":
    main()
