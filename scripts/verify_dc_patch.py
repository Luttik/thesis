# -*- coding: utf-8 -*-
"""Verify the §2.3/§5.1.1 tracked edits: simulate accept-all and reject-all,
and flag any deleted paragraph that still has non-deleted (surviving) text."""
import zipfile
from lxml import etree

DOCX = r"C:\workspace\thesis\Thesis Draft - Daan Luttik - MBA.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
def qn(t): return f"{{{W}}}{t}"

with zipfile.ZipFile(DOCX) as z:
    root = etree.fromstring(z.read("word/document.xml"))

def ancestors_tags(el, stop):
    out = []
    p = el.getparent()
    while p is not None and p is not stop:
        out.append(etree.QName(p).localname)
        p = p.getparent()
    return out

def para_accept(p):
    parts = []
    for t in p.iter(qn("t")):
        if "del" not in ancestors_tags(t, p):
            parts.append(t.text or "")
    return "".join(parts)

def para_reject(p):
    parts = []
    for el in p.iter():
        ln = etree.QName(el).localname
        if ln == "delText":
            parts.append(el.text or "")
        elif ln == "t" and "ins" not in ancestors_tags(el, p):
            parts.append(el.text or "")
    return "".join(parts)

def is_para_deleted(p):
    pPr = p.find(qn("pPr"))
    if pPr is None: return False
    rPr = pPr.find(qn("rPr"))
    return rPr is not None and rPr.find(qn("del")) is not None

def surviving_text_in_deleted(p):
    parts = []
    for t in p.iter(qn("t")):
        if "del" not in ancestors_tags(t, p):
            parts.append(t.text or "")
    return "".join(parts).strip()

paras = list(root.iter(qn("p")))

def find_idx(marker):
    for i, p in enumerate(paras):
        if marker in para_accept(p) or marker in para_reject(p):
            return i
    return None

i_23h = find_idx("Learnings from earlier waves")
i_24h = find_idx("Value theory and value creation with agentic AI")
i_511 = find_idx("Extending dynamic capabilities to agentic AI")
i_512 = find_idx("Value as configuration-in-use rather than capability")

print("=== ORPHAN CHECK (deleted paragraphs with surviving text) ===")
problems = 0
for i, p in enumerate(paras):
    if is_para_deleted(p):
        surv = surviving_text_in_deleted(p)
        if surv:
            problems += 1
            print(f"  [para {i}] ORPHAN: {surv!r}")
print(f"  -> {problems} orphan paragraph(s) found")

def show_range(lo, hi, label):
    print(f"\n=== {label}: ACCEPT-ALL result ===")
    for p in paras[lo:hi]:
        if is_para_deleted(p):
            continue
        txt = para_accept(p).strip()
        if txt:
            print("•", txt[:600] + ("..." if len(txt) > 600 else ""))

show_range(i_23h, i_24h, "2.3")
show_range(i_511, i_512, "5.1.1")

print("\n=== NEW REFERENCES (accept-all) ===")
for p in paras:
    txt = para_accept(p).strip()
    if txt.startswith("Teece, D. J."):
        print("•", txt)
