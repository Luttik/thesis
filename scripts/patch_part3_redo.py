# -*- coding: utf-8 -*-
"""Remove the Part-3 citations that drifted to wrong anchors and re-insert them at
verified text anchors. Keeps the two correct ones (Hanelt/Verhoef §1.2, Kumar §2.4).
[112] Enholm is dropped (the rewritten §2.3 paragraph already cites Enholm)."""
import copy, shutil
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP = ROOT / "Thesis Draft - Daan Luttik - MBA.part3redo-backup.docx"
AUTHOR, DATE = "Claude", "2026-06-07T00:00:00Z"
XS = "{http://www.w3.org/XML/1998/namespace}space"

def ftext(p): return "".join(t.text or "" for t in p.iter(qn("w:t")))
def used_ids(doc): return {int(e.get(qn("w:id"),0)) for e in doc.element.body.iter() if e.get(qn("w:id")) is not None}

def _mk_run(text, rpr):
    r = etree.Element(qn("w:r"))
    if rpr is not None:
        rr = copy.deepcopy(rpr)
        for bad in rr.findall(qn("w:ins"))+rr.findall(qn("w:del")): rr.remove(bad)
        if len(rr): r.append(rr)
    t = etree.SubElement(r, qn("w:t")); t.set(XS, "preserve"); t.text = text
    return r

def _wrap_ins(run, used):
    nid = max(used)+1; used.add(nid)
    ins = etree.Element(qn("w:ins")); ins.set(qn("w:id"),str(nid)); ins.set(qn("w:author"),AUTHOR); ins.set(qn("w:date"),DATE)
    ins.append(run); return ins

def insert_after_phrase(doc, phrase, text, used):
    for p in doc.paragraphs:
        el = p._element; runs = el.findall(qn("w:r"))
        full=""; spans=[]
        for r in runs:
            tt=r.find(qn("w:t")); s=tt.text if (tt is not None and tt.text) else ""
            spans.append((r,len(full),len(full)+len(s),s)); full+=s
        i = full.find(phrase)
        if i == -1: continue
        pos = i+len(phrase)
        for r,rs,re_,s in spans:
            if s=="" or not (rs < pos <= re_): continue
            cut=pos-rs; before,after=s[:cut],s[cut:]
            rpr=r.find(qn("w:rPr")); parent=r.getparent(); idx=list(parent).index(r); parts=[]
            if before: parts.append(_mk_run(before,rpr))
            parts.append(_wrap_ins(_mk_run(text,rpr),used))
            if after: parts.append(_mk_run(after,rpr))
            for j,pt in enumerate(parts): parent.insert(idx+j,pt)
            parent.remove(r); return True
    return False

REMOVE_EXACT = {
    " (Chintalapati & Pandey, 2022)", " (Cottier et al., 2024)",
    " (Brynjolfsson et al., 2025)", " (Wessel et al., 2021)",
    " (Enholm et al., 2022)", " (Lepak et al., 2007)",
}
RAG_PREFIX = "In other words, RAG supplements"

RAG_DEF = ("In other words, RAG supplements a model’s input with relevant text retrieved from an "
           "external knowledge source at query time, grounding its output in that material rather than "
           "in its training data alone (Gao et al., 2023). ")

REINSERT = [  # (anchor phrase, citation text)
    ("practitioner discourse", " (Chintalapati & Pandey, 2022)"),
    ("data and computation", " (Cottier et al., 2024)"),
    ("commercial performance", " (Huang & Rust, 2020)"),
    ("improved employee productivity", " (Brynjolfsson et al., 2025)"),
    ("sometimes organizational identity", " (Wessel et al., 2021)"),
    ("distinction between value creation and value capture", " (Lepak et al., 2007)"),
]

def main():
    shutil.copy(DOCX, BACKUP)
    doc = Document(str(DOCX)); body = doc.element.body; used = used_ids(doc)

    # 1. remove drifted insertions
    removed=[]
    for ins in list(body.iter(qn("w:ins"))):
        if ins.get(qn("w:author")) != AUTHOR: continue
        txt = "".join(t.text or "" for t in ins.iter(qn("w:t")))
        if txt in REMOVE_EXACT or txt.startswith(RAG_PREFIX):
            ins.getparent().remove(ins); removed.append(txt[:40])
    print("REMOVED:", len(removed))
    for r in removed: print("   -", repr(r))

    # 2. re-insert at verified text anchors
    print("RE-INSERT:")
    for phrase, text in REINSERT:
        ok = insert_after_phrase(doc, phrase, text, used)
        print(f"   {'ok ' if ok else 'FAIL'}: {text.strip()} -> after {phrase!r}")

    # 3. RAG definition after the (Lewis et al., 2020). sentence
    ok = insert_after_phrase(doc, "Lewis et al., 2020). ", RAG_DEF, used)
    print(f"   {'ok ' if ok else 'FAIL'}: RAG definition -> after 'Lewis et al., 2020). '")

    doc.save(str(DOCX))
    print(f"Saved. Backup: {BACKUP}")

if __name__ == "__main__":
    main()
