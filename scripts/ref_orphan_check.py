# -*- coding: utf-8 -*-
"""Find reference-list entries that are no longer cited in the body (orphans).
Uses the ACCEPT-ALL view (text inside <w:del> is ignored, so deleted mentions
don't count as usage)."""
import re, zipfile
from lxml import etree

DOCX = r"C:\workspace\thesis\Thesis Draft - Daan Luttik - MBA.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
def qn(t): return f"{{{W}}}{t}"

with zipfile.ZipFile(DOCX) as z:
    root = etree.fromstring(z.read("word/document.xml"))

def anc_has_del(el, stop):
    p = el.getparent()
    while p is not None and p is not stop:
        if etree.QName(p).localname == "del":
            return True
        p = p.getparent()
    return False

def accept_text(p):
    return "".join(t.text or "" for t in p.iter(qn("t")) if not anc_has_del(t, p))

def style(p):
    pPr = p.find(qn("pPr"))
    if pPr is None: return ""
    ps = pPr.find(qn("pStyle"))
    return (ps.get(qn("val")) if ps is not None else "") or ""

paras = [(style(p), accept_text(p)) for p in root.iter(qn("p"))]

# locate references section: from "7 ... References" Heading1 to next Heading1
ref_start = next(i for i,(s,t) in enumerate(paras)
                 if s.startswith("Heading1") and "References" in t)
ref_end = next((i for i in range(ref_start+1, len(paras))
                if paras[i][0].startswith("Heading1")), len(paras))

body_text = " ".join(t for i,(s,t) in enumerate(paras) if not (ref_start <= i < ref_end))
ref_paras = [t for (s,t) in paras[ref_start+1:ref_end] if t.strip()]

def parse_ref(text):
    m = re.match(r"\s*(.+?)\s*\((\d{4})", text)
    if not m: return None
    authors, year = m.group(1), m.group(2)
    surname = authors.split(",")[0].strip().rstrip(".") if "," in authors else authors.strip().rstrip(".")
    return surname, year

def used(surname, year):
    short = surname.split()[0]
    positions = [m.start() for m in re.finditer(re.escape(year), body_text)]
    near = any((surname in body_text[max(0,p-75):p]) or (short in body_text[max(0,p-75):p]) for p in positions)
    anywhere = (surname in body_text) or (short in body_text)
    if near: return "USED"
    return "ORPHAN" if not anywhere else "CHECK (author present, not near this year)"

print(f"References section paras {ref_start}..{ref_end}  | {len(ref_paras)} entries\n")
orphans, checks = [], []
for t in ref_paras:
    pr = parse_ref(t)
    if not pr:
        continue
    surname, year = pr
    st = used(surname, year)
    label = f"{surname} ({year})"
    if st == "USED": continue
    (orphans if st == "ORPHAN" else checks).append((label, t[:90]))

print("=== ORPHANS (author surname never appears in body) ===")
for lbl, snip in orphans: print(f"  • {lbl}")
print(f"\n=== CHECK (author appears, but not next to this year) ===")
for lbl, snip in checks: print(f"  • {lbl}  ::  {snip}")
print(f"\n{len(orphans)} orphan(s), {len(checks)} to check, out of {len(ref_paras)} entries.")
