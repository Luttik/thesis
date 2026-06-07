"""Two-way reference check on the ACCEPT-ALL-CHANGES view (w:t only, deleted text excluded)."""
import re, unicodedata
from lxml import etree
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def w(t): return W+t
ns={'w':W[1:-1]}

def norm(s):
    s=unicodedata.normalize('NFKD',s); s=''.join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()
def acc(p):  # accepted text: w:t only (skips w:delText)
    return ''.join(t.text or '' for t in p.iter(w('t')))
def first_surname(s):
    m=re.match(r"([A-Za-zÀ-ÿ'’\-]+)", s); return m.group(1) if m else '?'

t=etree.parse('word/document.xml'); body=t.getroot().find(w('body'))

# references
refs=[]; in_ref=False
for p in body.findall(w('p')):
    txt=acc(p); pStyle=p.find('.//w:pStyle',ns); st=pStyle.get(w('val')) if pStyle is not None else None
    if st=='Heading1' and txt.strip().startswith('7.') and 'Reference' in txt: in_ref=True; continue
    if in_ref and st=='Heading1': break
    if in_ref and txt.strip(): refs.append(txt.strip())
ref_keys=[]
for r in refs:
    sn=norm(first_surname(r)); ym=re.search(r'\(?((?:19|20)\d{2})',r); ref_keys.append((sn, ym.group(1) if ym else '????', r[:60]))
ref_set={(s,y) for s,y,_ in ref_keys}

# body (excl ref section), + notes
chunks=[]; in_ref=False
for p in body.findall(w('p')):
    txt=acc(p); pStyle=p.find('.//w:pStyle',ns); st=pStyle.get(w('val')) if pStyle is not None else None
    if st=='Heading1' and txt.strip().startswith('7.') and 'Reference' in txt: in_ref=True; continue
    if in_ref and st=='Heading1': in_ref=False
    if not in_ref: chunks.append(txt)
text='\n'.join(chunks)
for fn in ['word/footnotes.xml','word/endnotes.xml']:
    try:
        ft=etree.parse(fn); text+='\n'+''.join(x.text or '' for x in ft.getroot().iter(w('t')))
    except Exception: pass

cite_re=re.compile(r"([A-Z][A-Za-zÀ-ÿ'’\.\-]+(?:\s+et\s+al\.?)?(?:\s*&\s*[A-Z][A-Za-zÀ-ÿ'’\-]+)?(?:\s+(?:and|&)\s+[A-Z][A-Za-zÀ-ÿ'’\-]+)?)[\s,]*\(?((?:19|20)\d{2})")
intext=set(); raw=[]
for m in cite_re.finditer(text):
    ph=m.group(1).strip().rstrip('.'); yr=m.group(2); sn=norm(first_surname(ph))
    intext.add((sn,yr)); raw.append((sn,yr,ph))

print("A. ORPHAN CITATIONS (accepted view)")
orph=sorted({(s,y) for s,y in intext if (s,y) not in ref_set})
for s,y in orph:
    alt=sorted({k[1] for k in ref_set if k[0]==s})
    ex=next((p for ss,yy,p in raw if ss==s and yy==y),'')
    print(f"  - {ex} ({y})  ::  {'YEAR ref has '+str(alt) if alt else 'ABSENT from refs'}")
if not orph: print("  (none)")

print("\nB. UNCITED REFERENCES (accepted view)")
un=0
for s,y,prev in ref_keys:
    if (s,y) not in intext:
        un+=1; alt=sorted({yy for ss,yy in intext if ss==s})
        print(f"  - {prev} ({y})  ::  {'cited under '+str(alt) if alt else 'NEVER cited'}")
if not un: print("  (none)")

# duplicate ref surnames
from collections import Counter
c=Counter(s for s,_,_ in ref_keys)
dups=[(s,n) for s,n in c.items() if n>1]
print("\nC. DUPLICATE-SURNAME REF ENTRIES:", dups if dups else "(none)")
print(f"\nTOTALS: {len(refs)} refs | {len(intext)} cite-keys | {len(orph)} orphan | {un} uncited")
