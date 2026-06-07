import re, unicodedata
from lxml import etree

W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def w(t): return W+t
ns={'w':W[1:-1]}

t=etree.parse('word/document.xml')
body=t.getroot().find(w('body'))

# Walk paragraphs, tracking current heading, collect (heading, text)
rows=[]
cur_ch='(front matter)'; cur_sec=''
in_ref=False
for p in body.findall(w('p')):
    txt=''.join(p.itertext()).strip()
    pStyle=p.find('.//w:pStyle',ns)
    st=pStyle.get(w('val')) if pStyle is not None else None
    if st=='Heading1':
        cur_ch=txt; cur_sec=''
        in_ref = txt.startswith('7.') and 'Reference' in txt
    elif st in ('Heading2','Heading3') and not in_ref:
        cur_sec=txt
    if not in_ref and txt:
        rows.append((cur_ch,cur_sec,txt))

# terms to locate: each is (label, regex)
terms = [
  ("Agrawal 2023", r"Agrawal"),
  ("Ancillai 2023", r"Ancillai"),
  ("Bessen 2018", r"Bessen"),
  ("Doshi & Hauser 2024", r"Doshi"),
  ("Ellstrom 2021", r"Ellstr"),
  ("Enholm 2022", r"Enholm"),
  ("Hanelt 2021", r"Hanelt"),
  ("Heimbach 2015", r"Heimbach"),
  ("Kaartemo & Helkkula 2018", r"Kaartemo"),
  ("Kitsios & Kamariotou 2021", r"Kitsios"),
  ("Leone 2020", r"Leone"),
  ("Lincoln & Guba 1985", r"Lincoln"),
  ("Radford 2018", r"Radford"),
  ("Verhoef 2021", r"Verhoef"),
  ("Warner & Wager 2019", r"Warner"),
  ("Wessel 2021", r"Wessel"),
  ("Yao 2023", r"Yao"),
  ("Vaswani (year?)", r"Vaswani"),
  ("Grewal (year?)", r"Grewal"),
  ("Charmaz (year?)", r"Charmaz"),
  ("Abou Elgheit/Elgeit", r"Elg[he]*it"),
  ("Blumer", r"Blumer"),
]

for label,rx in terms:
    hits=[]
    for ch,sec,txt in rows:
        for m in re.finditer(rx, txt):
            s=max(0,m.start()-45); e=min(len(txt),m.end()+45)
            loc = ch.split('\t')[0].strip()[:26]
            if sec: loc+=" › "+sec.split('\t')[0].strip()[:30]
            hits.append((loc, "…"+txt[s:e].replace('\n',' ')+"…"))
    print(f"### {label}  ({len(hits)} hit(s))")
    seen=set()
    for loc,snip in hits:
        key=(loc,snip[:40])
        if key in seen: continue
        seen.add(key)
        print(f"   [{loc}]  {snip}")
    print()
