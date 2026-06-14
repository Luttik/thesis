# -*- coding: utf-8 -*-
"""Extensive automated scan of the thesis (accepted-changes view)."""
import re, zipfile, collections
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
def acc(p): return "".join((t.text or "") for t in p.iter(q("t")) if not inside_del(t))
def style(p):
    pPr = p.find(q("pPr"))
    if pPr is not None:
        ps = pPr.find(q("pStyle"))
        if ps is not None: return ps.get(q("val")) or ""
    return ""

paras = list(body.iter(q("p")))
texts = [acc(p) for p in paras]
styles = [style(p) for p in paras]

# reference section bounds
rs = re_ = None
for i,p in enumerate(paras):
    if rs is None and styles[i]=="Heading1" and "References" in texts[i]: rs=i
    elif rs is not None and styles[i]=="Heading1" and "Appendix" in texts[i]: re_=i; break
if re_ is None: re_=len(paras)
body_text = "\n".join(texts[i] for i in range(len(paras)) if not (rs<=i<re_))

print("="*70)
print("1. HEADINGS (number + text) — look for empty/placeholder/odd numbering")
print("="*70)
for i,p in enumerate(paras):
    if styles[i].startswith("Heading"):
        t = texts[i].strip()
        flag = "  <<< EMPTY/SHORT" if len(t)<=3 else ("  <<< PLACEHOLDER" if re.search(r"TEMP|TODO|XXX|\bTBD\b", t) else "")
        print(f"  [{styles[i]:9}] {t[:75]!r}{flag}")

print("\n"+"="*70)
print("2. PLACEHOLDER / EDITING ARTIFACTS in body")
print("="*70)
for i in range(len(paras)):
    if rs<=i<re_: continue
    for m in re.finditer(r"\b(TEMP|TODO|FIXME|XXX|TBD|\?\?\?|\[\s*\]|lorem)\b", texts[i], re.I):
        print(f"  para{i}: …{texts[i][max(0,m.start()-30):m.start()+30]}…")

print("\n"+"="*70)
print("3. CROSS-REFERENCES (Section/Table/Figure/Appendix/Chapter)")
print("="*70)
refs = collections.Counter()
for i in range(len(paras)):
    if rs<=i<re_: continue
    for m in re.finditer(r"(Section|Table|Figure|Appendix|Chapter)\s+([A-Z]?\d+(?:\.\d+)*)", texts[i]):
        refs[(m.group(1), m.group(2))]+=1
for (k,v),c in sorted(refs.items()):
    print(f"  {k} {v}  x{c}")

print("\n"+"="*70)
print("4. DOUBLE SPACES / SPACE-BEFORE-PUNCT / REPEATED WORDS")
print("="*70)
for i in range(len(paras)):
    t=texts[i]
    if "  " in t.replace("\t",""):
        for m in re.finditer(r"\S(  +)\S", t):
            seg=t[max(0,m.start()-20):m.start()+22].replace("\n"," ")
            print(f"  [dbl-space] p{i}: …{seg}…")
            break
    for m in re.finditer(r"\s[,;:]", t):
        print(f"  [space-before-punct] p{i}: …{t[max(0,m.start()-18):m.start()+10]}…")
    for m in re.finditer(r"\b(\w+)\s+\1\b", t):
        if m.group(1).lower() not in ("that","had","very","the"):  # 'that that' sometimes ok-ish but flag rare
            print(f"  [repeat-word '{m.group(1)}'] p{i}: …{t[max(0,m.start()-15):m.start()+25]}…")

print("\n"+"="*70)
print("5. STRAIGHT QUOTES / EM-DASH / spelled-out interviewee")
print("="*70)
for i in range(len(paras)):
    t=texts[i]
    if '"' in t or re.search(r"\w'\w?", t) and "'" in t:
        if '"' in t: print(f"  [straight-double-quote] p{i}: …{t[t.find(chr(34))-15:t.find(chr(34))+15]}…")
    if "—" in t:
        print(f"  [em-dash] p{i}: …{t[t.find('—')-20:t.find('—')+20]}…")
    for m in re.finditer(r"interviewee (one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)", t, re.I):
        print(f"  [spelled-interviewee] p{i}: …{t[max(0,m.start()-10):m.start()+30]}…")

print("\n"+"="*70)
print("6. CITED-BUT-MISSING (in-text citation with no reference entry)")
print("="*70)
# ref surnames+years
def fa_year(entry):
    ym=re.search(r"\((\d{4})", entry); year=ym.group(1) if ym else None
    cut=len(entry)
    for ch in [",","("]:
        k=entry.find(ch)
        if k!=-1: cut=min(cut,k)
    return entry[:cut].strip().rstrip(". ").strip(), year
refset=set()
refsurnames=set()
for i in range(rs+1,re_):
    e=texts[i].strip()
    if len(e)<8: continue
    s,y=fa_year(e)
    if s and y: refset.add((s,y)); refsurnames.add(s)
# narrative citations Surname (et al.|& X|and X)? (year)
seen=set()
for m in re.finditer(r"\b([A-Z][\wÀ-ÿ’'\-]+)\s*(?:et al\.|&\s*[A-Z][\wÀ-ÿ’'\-]+|and\s+[A-Z][\wÀ-ÿ’'\-]+)?\s*\((\d{4})[a-z]?\)", body_text):
    s,y=m.group(1),m.group(2)
    if s in ("Figure","Table","Section","Appendix","Chapter"): continue
    if (s,y) in seen: continue
    seen.add((s,y))
    if (s,y) not in refset and s not in refsurnames:
        print(f"  [narrative] {s} ({y}) — no matching reference entry")
# parenthetical citations: scan inside parens for Surname, year
for m in re.finditer(r"\(([^()]*\d{4}[^()]*)\)", body_text):
    inside=m.group(1)
    for cm in re.finditer(r"([A-Z][\wÀ-ÿ’'\-]+)(?:\s+et al\.|\s*&\s*[A-Z][\wÀ-ÿ’'\-]+)?,\s*(\d{4})", inside):
        s,y=cm.group(1),cm.group(2)
        if (s,y) in seen: continue
        seen.add((s,y))
        if (s,y) not in refset and s not in refsurnames:
            print(f"  [parenthetical] {s} ({y}) — no matching reference entry  | in: ({inside[:50]})")

print("\n"+"="*70)
print("7. et al. period/comma re-check")
print("="*70)
hit=False
for i in range(len(paras)):
    if rs<=i<re_: continue
    for m in re.finditer(r"et al[^A-Za-z.]", texts[i]):
        print(f"  [no-period] p{i}: …{texts[i][max(0,m.start()-20):m.start()+12]}…"); hit=True
    for m in re.finditer(r"et al\.\s+\d{4}", texts[i]):
        print(f"  [missing-comma] p{i}: …{texts[i][max(0,m.start()-20):m.start()+14]}…"); hit=True
if not hit: print("  (clean)")
print("\nDONE")
