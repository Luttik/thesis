"""Extract every comment with its anchored body text, to a UTF-8 file."""
import zipfile, json
from xml.etree import ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
SRC = 'Thesis Draft - Daan Luttik - MBA - copy from 2026-06-14.docx'

z = zipfile.ZipFile(SRC)
croot = ET.fromstring(z.read('word/comments.xml'))
comments = {}
for c in croot.findall(W+'comment'):
    cid = c.get(W+'id')
    comments[cid] = {
        'id': cid,
        'author': c.get(W+'author'),
        'date': c.get(W+'date'),
        'text': ''.join(t.text or '' for t in c.iter(W+'t')),
        'anchor': '',
    }

# Walk document.xml to capture anchored text between commentRangeStart/End
droot = ET.fromstring(z.read('word/document.xml'))
active = set()
buf = {}
for el in droot.iter():
    tag = el.tag
    if tag == W+'commentRangeStart':
        cid = el.get(W+'id'); active.add(cid); buf.setdefault(cid, [])
    elif tag == W+'commentRangeEnd':
        cid = el.get(W+'id'); active.discard(cid)
    elif tag == W+'t':
        if el.text:
            for cid in active:
                buf[cid].append(el.text)
for cid, parts in buf.items():
    if cid in comments:
        comments[cid]['anchor'] = ''.join(parts)

# Order by id numerically
out = sorted(comments.values(), key=lambda d: int(d['id']))
with open('scripts/_comments_dump.txt', 'w', encoding='utf-8') as f:
    for d in out:
        f.write('='*90 + '\n')
        f.write('#%s | %s | %s\n' % (d['id'], d['author'], d['date']))
        f.write('ANCHORED TO: %r\n' % (d['anchor'][:400]))
        f.write('COMMENT: %s\n' % d['text'])
print('wrote', len(out), 'comments to scripts/_comments_dump.txt')
