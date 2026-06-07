import re, unicodedata
from lxml import etree

W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def w(t): return W+t
ns={'w':W[1:-1]}

def norm(s):
    s=unicodedata.normalize('NFKD',s)
    s=''.join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()

def first_surname(phrase):
    m=re.match(r"([A-Za-zÀ-ÿ'’\-]+)", phrase)
    return m.group(1) if m else '?'

# ---------- 1. Reference list ----------
t=etree.parse('word/document.xml')
body=t.getroot().find(w('body'))
refs=[]
in_ref=False
for p in body.findall(w('p')):
    txt=''.join(p.itertext())
    pStyle=p.find('.//w:pStyle',ns)
    st=pStyle.get(w('val')) if pStyle is not None else None
    if st=='Heading1' and txt.strip().startswith('7.') and 'Reference' in txt:
        in_ref=True; continue
    if in_ref and st=='Heading1': break
    if in_ref and txt.strip(): refs.append(txt.strip())

def parse_ref(r):
    surname=first_surname(r)
    ym=re.search(r'\(?((?:19|20)\d{2})([a-z]?)\)?', r)
    year=ym.group(1) if ym else '????'
    return norm(surname), year, surname

ref_keys=[]
for r in refs:
    sn,yr,orig=parse_ref(r)
    ref_keys.append((sn,yr,orig,r[:75]))

# ---------- 2. Body text (exclude ref section), include appendices + notes ----------
chunks=[]
in_ref=False
for p in body.findall(w('p')):
    txt=''.join(p.itertext())
    pStyle=p.find('.//w:pStyle',ns)
    st=pStyle.get(w('val')) if pStyle is not None else None
    if st=='Heading1' and txt.strip().startswith('7.') and 'Reference' in txt:
        in_ref=True
        continue
    if in_ref and st=='Heading1':
        in_ref=False  # appendix begins
    if not in_ref:
        chunks.append(txt)
text='\n'.join(chunks)
for fn in ['word/footnotes.xml','word/endnotes.xml']:
    try:
        ft=etree.parse(fn); text+='\n'+''.join(ft.getroot().itertext())
    except Exception: pass

# ---------- 3. In-text citations ----------
cite_re=re.compile(
    r"([A-Z][A-Za-zÀ-ÿ'’\.\-]+"
    r"(?:\s+et\s+al\.?)?"
    r"(?:\s*&\s*[A-Z][A-Za-zÀ-ÿ'’\-]+)?"
    r"(?:\s+(?:and|&)\s+[A-Z][A-Za-zÀ-ÿ'’\-]+)?)"
    r"[\s,]*\(?((?:19|20)\d{2})([a-z]?)\)?")
intext=set()
intext_raw=[]
for m in cite_re.finditer(text):
    phrase=m.group(1).strip().rstrip('.')
    year=m.group(2)
    sn=norm(first_surname(phrase))
    intext.add((sn,year))
    intext_raw.append((sn,year,phrase))

ref_set={(sn,yr) for sn,yr,_,_ in ref_keys}

print("="*72)
print("A. ORPHAN CITATIONS  (in text, but NO matching reference entry)")
print("="*72)
orphans=sorted({(sn,yr) for sn,yr in intext if (sn,yr) not in ref_set})
if not orphans: print("  (none)")
for sn,yr in orphans:
    alt=sorted({k[1] for k in ref_set if k[0]==sn})
    if alt:
        flag=f"YEAR MISMATCH -> ref has {alt}"
    else:
        flag="surname ABSENT from reference list"
    sample=next((p for s,y,p in intext_raw if s==sn and y==yr),'')
    print(f"  - {sample} ({yr})  ::  {flag}")

print()
print("="*72)
print("B. UNCITED REFERENCES  (in reference list, but NEVER cited in text)")
print("="*72)
any_un=False
for sn,yr,orig,preview in ref_keys:
    if (sn,yr) not in intext:
        any_un=True
        alt=sorted({y for s,y in intext if s==sn})
        flag=f"cited under year(s) {alt}" if alt else "surname NEVER cited"
        print(f"  - {orig} ({yr})  ::  {flag}")
if not any_un: print("  (none)")

print()
print("="*72)
print(f"TOTALS: {len(refs)} references | {len(intext)} distinct in-text (surname,year) keys "
      f"| {len(orphans)} orphan citation keys | "
      f"{sum(1 for sn,yr,_,_ in ref_keys if (sn,yr) not in intext)} uncited refs")
