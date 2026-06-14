# -*- coding: utf-8 -*-
"""Find orphan references (in the reference list but never cited in the body)
and audit every 'et al' for missing period / comma. Accepted-changes view."""
import re, zipfile
from lxml import etree

DOCX = r"C:\workspace\thesis\Thesis Draft - Daan Luttik - MBA - copy from 2026-06-14.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
def q(t): return f"{{{W}}}{t}"

root = etree.fromstring(zipfile.ZipFile(DOCX).read("word/document.xml"))
body = root.find(q("body"))

def inside_del(el):
    a = el.getparent()
    while a is not None:
        if a.tag == q("del"): return True
        a = a.getparent()
    return False

def acc_text(p):
    return "".join((t.text or "") for t in p.iter(q("t")) if not inside_del(t))

def style(p):
    pPr = p.find(q("pPr"))
    if pPr is not None:
        ps = pPr.find(q("pStyle"))
        if ps is not None: return ps.get(q("val")) or ""
    return ""

paras = list(body.iter(q("p")))
texts = [acc_text(p) for p in paras]

# Locate reference section: from "References" Heading1 to "Appendix A"
ref_start = ref_end = None
for i, p in enumerate(paras):
    st = style(p); tx = texts[i]
    if ref_start is None and st == "Heading1" and "References" in tx:
        ref_start = i
    elif ref_start is not None and st == "Heading1" and "Appendix" in tx:
        ref_end = i; break
if ref_end is None: ref_end = len(paras)
print(f"Reference section: paragraphs {ref_start}..{ref_end}")

ref_paras = list(range(ref_start + 1, ref_end))
# body text excludes the reference list block
body_text = "\n".join(texts[i] for i in range(len(paras)) if not (ref_start <= i < ref_end))

def first_author_year(entry):
    ym = re.search(r"\((\d{4})", entry)
    year = ym.group(1) if ym else None
    # surname = up to first comma, or up to first '(' , or first '.'
    cut = len(entry)
    for ch in [",", "("]:
        k = entry.find(ch)
        if k != -1: cut = min(cut, k)
    head = entry[:cut].strip()
    # org authors like 'Anthropic.' -> strip trailing period
    head = head.rstrip(". ").strip()
    return head, year

print("\n=== REFERENCE AUDIT (orphan = surname+year not found in body) ===")
orphans = []
for i in ref_paras:
    entry = texts[i].strip()
    if len(entry) < 8:  # skip blanks
        continue
    surname, year = first_author_year(entry)
    if not year or not surname:
        print(f"  [?] could not parse: {entry[:60]!r}")
        continue
    # search body for surname within 40 chars before year
    pat = re.escape(surname) + r".{0,40}?" + re.escape(year)
    cited = re.search(pat, body_text) is not None
    if not cited:
        # also try year-before-surname (rare) and bare surname+year loose
        cited = re.search(re.escape(surname) + r"[^\n]{0,60}?" + year, body_text) is not None
    if not cited:
        orphans.append((surname, year, entry[:70]))
    print(f"  {'CITED ' if cited else 'ORPHAN'}  {surname} ({year})")

print("\n=== ORPHAN CANDIDATES ===")
for s, y, e in orphans:
    print(f"  - {s} ({y}): {e}")

print("\n=== 'et al' AUDIT (body, accepted view) ===")
# find every 'et al' and 12 chars of trailing context
for m in re.finditer(r"et al[^A-Za-z]{0,8}\d{0,4}", body_text):
    seg = m.group(0)
    # flag: 'et al' not followed by '.'  OR  'et al.' followed by space+digit (missing comma)
    after = body_text[m.start(): m.start()+14]
    no_period = bool(re.match(r"et al[^.]", after)) or after.strip() == "et al"
    missing_comma = bool(re.search(r"et al\.\s+\d{4}", after))  # 'et al. 2024' w/o comma (narrative ok if '(' before year)
    if no_period or missing_comma:
        ctx = body_text[max(0,m.start()-25): m.start()+18].replace("\n"," ")
        tag = []
        if no_period: tag.append("NO-PERIOD")
        if missing_comma: tag.append("MAYBE-MISSING-COMMA")
        print(f"  [{'/'.join(tag)}] …{ctx}…")
