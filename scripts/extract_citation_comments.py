import re
from lxml import etree

W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def w(t): return W+t
ns={'w':W[1:-1]}

# comments of interest: the "citation needed" family
TARGET = ['28','30','40','46','47','72','99','104','107','112','123','125','102']

# load comment texts
ct=etree.parse('word/comments.xml')
ctext={}
for c in ct.getroot().iter(w('comment')):
    ctext[c.get(w('id'))]=''.join(c.itertext()).strip()

t=etree.parse('word/document.xml')
body=t.getroot().find(w('body'))

# Build a flat ordered list of (kind, payload) across the doc, tracking headings,
# and capture text inside each comment range.
cur_ch='(front)'; cur_sec=''
# We capture per-paragraph: track open comment ranges and accumulate their text
open_ranges={}   # id -> list of text fragments
captured={}      # id -> {'text':..., 'ch':..., 'sec':..., 'before':..., 'after':...}
recent_text=[]   # rolling buffer of recent plain text for "before" context

for p in body.findall(w('p')):
    pStyle=p.find('.//w:pStyle',ns)
    st=pStyle.get(w('val')) if pStyle is not None else None
    full=''.join(p.itertext())
    if st=='Heading1':
        cur_ch=full.strip(); cur_sec=''
    elif st in ('Heading2','Heading3'):
        cur_sec=full.strip()
    # walk in document order
    para_before=''  # text seen so far in this paragraph
    for el in p.iter():
        tag=el.tag
        if tag==w('commentRangeStart'):
            cid=el.get(w('id'))
            if cid in TARGET:
                open_ranges[cid]=[]
                captured.setdefault(cid,{})['ch']=cur_ch
                captured[cid]['sec']=cur_sec
                captured[cid]['before']=(para_before[-160:])
        elif tag==w('commentRangeEnd'):
            cid=el.get(w('id'))
            if cid in open_ranges:
                captured[cid]['text']=''.join(open_ranges[cid]).strip()
                captured[cid]['after_para']=full
                del open_ranges[cid]
        elif tag==w('t'):
            txt=el.text or ''
            para_before+=txt
            for cid in open_ranges:
                open_ranges[cid].append(txt)
        elif tag==w('tab'):
            para_before+='\t'
            for cid in open_ranges:
                open_ranges[cid].append(' ')

print("CITATION-NEEDED COMMENTS  (anchored statement + supervisor note)\n"+"="*72)
for cid in TARGET:
    info=captured.get(cid,{})
    loc=info.get('ch','?').split('\t')[0].strip()[:30]
    sec=info.get('sec','').split('\t')[0].strip()[:34]
    where=loc+(' › '+sec if sec else '')
    print(f"\n[{cid}]  ({where})")
    print(f"  SUPERVISOR: {ctext.get(cid,'?')}")
    anchored=info.get('text','').strip()
    if not anchored:
        # fall back to context before
        anchored='(zero-length anchor) context before: ...'+info.get('before','').strip()[-140:]
    print(f"  ANCHORED:   “{anchored[:400]}”")
