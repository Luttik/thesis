# -*- coding: utf-8 -*-
"""Add 7 missing reference-list entries (APA 7, cloned formatting), cite 3 sources in §2.2,
and fix small consistency issues (Cieslak year; Ellstrom/Holmstrom spelling). Tracked, author 'Claude'."""
from __future__ import annotations
import copy, shutil
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP = ROOT / "Thesis Draft - Daan Luttik - MBA.refs-backup.docx"
AUTHOR = "Claude"; DATE = "2026-06-07T21:00:00Z"
XS = "{http://www.w3.org/XML/1998/namespace}space"
NBSP = " "; ENDASH = "–"

def used_ids(doc):
    return {int(el.get(qn("w:id"), 0)) for el in doc.element.body.iter() if el.get(qn("w:id")) is not None}
def nid(u): n = max(u, default=0) + 1; u.add(n); return n
def atext(el): return "".join(t.text or "" for t in el.iter(qn("w:t")))
def find(doc, marker):
    for p in doc.paragraphs:
        if marker in atext(p._element):
            return p._element
    return None

def _ins(used):
    ins = etree.Element(qn("w:ins")); ins.set(qn("w:id"), str(nid(used)))
    ins.set(qn("w:author"), AUTHOR); ins.set(qn("w:date"), DATE); return ins

def _refrun(text, italic):
    r = etree.Element(qn("w:r")); rPr = etree.SubElement(r, qn("w:rPr"))
    if italic:
        etree.SubElement(rPr, qn("w:i")); etree.SubElement(rPr, qn("w:iCs"))
    hl = etree.SubElement(rPr, qn("w:highlight")); hl.set(qn("w:val"), "white")
    t = etree.SubElement(r, qn("w:t")); t.set(XS, "preserve"); t.text = text
    return r

def ref_para(authors_title, journal, volume, tail, used):
    """Reference-list paragraph matching the existing style (spacing 360, hanging indent,
    italic journal+volume, highlight white); runs wrapped in <w:ins>."""
    p = etree.Element(qn("w:p"))
    pPr = etree.SubElement(p, qn("w:pPr"))
    sp = etree.SubElement(pPr, qn("w:spacing")); sp.set(qn("w:line"), "360"); sp.set(qn("w:lineRule"), "auto")
    ind = etree.SubElement(pPr, qn("w:ind")); ind.set(qn("w:left"), "720"); ind.set(qn("w:hanging"), "720")
    pr = etree.SubElement(pPr, qn("w:rPr")); hl = etree.SubElement(pr, qn("w:highlight")); hl.set(qn("w:val"), "white")
    ins = _ins(used)
    ins.append(_refrun(authors_title, False))
    ins.append(_refrun(journal, True))
    ins.append(_refrun("," + NBSP, False))
    ins.append(_refrun(volume, True))
    ins.append(_refrun(tail, False))
    p.append(ins)
    return p

def append_ins(p, text, used):
    ins = _ins(used); r = etree.SubElement(ins, qn("w:r")); t = etree.SubElement(r, qn("w:t"))
    t.set(XS, "preserve"); t.text = text; p.append(ins)

def replace_frag(p, old, new, used):
    runs = p.findall(qn("w:r")); segs, total = [], ""
    for r in runs:
        t = r.find(qn("w:t")); txt = t.text if (t is not None and t.text) else ""
        segs.append((r, txt)); total += txt
    s = total.find(old)
    if s < 0: return False
    e = s + len(old)
    def mk(rPr, x):
        nr = etree.Element(qn("w:r"))
        if rPr is not None: nr.append(copy.deepcopy(rPr))
        tt = etree.SubElement(nr, qn("w:t")); tt.set(XS, "preserve"); tt.text = x; return nr
    def dl(rPr, x):
        d = etree.Element(qn("w:del")); d.set(qn("w:id"), str(nid(used)))
        d.set(qn("w:author"), AUTHOR); d.set(qn("w:date"), DATE)
        rr = etree.SubElement(d, qn("w:r"))
        if rPr is not None: rr.insert(0, copy.deepcopy(rPr))
        dt = etree.SubElement(rr, qn("w:delText")); dt.set(XS, "preserve"); dt.text = x; return d
    def insr(rPr, x):
        i = etree.Element(qn("w:ins")); i.set(qn("w:id"), str(nid(used)))
        i.set(qn("w:author"), AUTHOR); i.set(qn("w:date"), DATE); i.append(mk(rPr, x)); return i
    pos = 0; done = False
    for r, txt in segs:
        rs, re_ = pos, pos + len(txt); pos = re_
        if not txt or re_ <= s or rs >= e: continue
        rPr = r.find(qn("w:rPr")); ls = max(s, rs) - rs; le = min(e, re_) - rs
        before, mid, after = txt[:ls], txt[ls:le], txt[le:]
        parent = r.getparent(); idx = list(parent).index(r); parts = []
        if before: parts.append(mk(rPr, before))
        if not done: parts.append(insr(rPr, new)); done = True
        if mid: parts.append(dl(rPr, mid))
        if after: parts.append(mk(rPr, after))
        for j, prt in enumerate(parts): parent.insert(idx + j, prt)
        parent.remove(r)
    return done

# 7 entries (anchor = start text of the existing entry to insert AFTER)
ENTRIES = [
 ("Almquist, E., Senior",
  "Ancillai, C., Sabatini, A., Gatti, M., & Perna, A. (2023). Digital technology and business model innovation: A systematic literature review and future research agenda. ",
  "Technological Forecasting and Social Change", "188", ", 122307. https://doi.org/10.1016/j.techfore.2022.122307"),
 ("Devlin, J., Chang",
  "Doshi, A. R., & Hauser, O. P. (2024). Generative AI enhances individual creativity but reduces the collective diversity of novel content. ",
  "Science Advances", "10", "(28), eadn5290. https://doi.org/10.1126/sciadv.adn5290"),
 ("Järvinen, J., & Taiminen",
  "Kaartemo, V., & Helkkula, A. (2018). A systematic review of artificial intelligence and robots in value co-creation: Current status and future research avenues. ",
  "Journal of Creating Value", "4", "(2), 211" + ENDASH + "228. https://doi.org/10.1177/2394964318805625"),
 ("LeCun, Y., Bengio",
  "Leone, D., Schiavone, F., Appio, F. P., & Chiao, B. (2020). How does artificial intelligence enable and enhance value co-creation in industrial markets? An exploratory case study in the healthcare ecosystem. ",
  "Journal of Business Research", "129", ", 849" + ENDASH + "859. https://doi.org/10.1016/j.jbusres.2020.11.008"),
 ("Wahid, R., Mero",
  "Warner, K. S. R., & Wäger, M. (2019). Building dynamic capabilities for digital transformation: An ongoing process of strategic renewal. ",
  "Long Range Planning", "52", "(3), 326" + ENDASH + "349. https://doi.org/10.1016/j.lrp.2018.12.001"),
]
ELLSTROM = ("Ellström, D., Holtström, J., Berg, E., & Josefsson, C. (2021). Dynamic capabilities for digital transformation. ",
  "Journal of Strategy and Management", "15", "(2), 272" + ENDASH + "286. https://doi.org/10.1108/JSMA-04-2021-0089")
ENHOLM = ("Enholm, I. M., Papagiannidis, E., Mikalef, P., & Krogstie, J. (2022). Artificial intelligence and business value: A literature review. ",
  "Information Systems Frontiers", "24", "(5), 1709" + ENDASH + "1734. https://doi.org/10.1007/s10796-021-10186-w")


def main():
    doc = Document(str(DOCX)); used = used_ids(doc)

    # ---- Gap A: cite Cieslak, Weber, Romeo in §2.2 ----
    p22 = find(doc, "organizational adoption literature reinforces")
    assert p22 is not None, "§2.2 paragraph missing"
    append_ins(p22, " More recent work locates the decisive factors in organizational readiness and "
        "capability: employee resistance to change can undermine AI readiness (Cieslak & Valor, 2025), "
        "and realizing value depends on building the organizational capabilities for AI implementation "
        "and on navigating the drivers and barriers of adoption (Weber et al., 2023; Romeo & Lacko, 2026).", used)
    print("Gap A: §2.2 citations added")

    # ---- Gap B: insert 7 reference-list entries alphabetically ----
    n = 0
    for anchor_txt, at, jr, vol, tail in ENTRIES:
        a = find(doc, anchor_txt)
        assert a is not None, f"ref anchor missing: {anchor_txt}"
        a.addnext(ref_para(at, jr, vol, tail, used)); n += 1
    # Ellström + Enholm after the 'Abou Elgheit' entry
    abou = find(doc, "Abou Elgheit")
    assert abou is not None, "Abou Elgheit anchor missing"
    pe = ref_para(*ELLSTROM, used); abou.addnext(pe); n += 1
    pe.addnext(ref_para(*ENHOLM, used)); n += 1
    print(f"Gap B: {n} reference-list entries inserted")

    # ---- Gap C (best-effort consistency) ----
    cie = find(doc, "Cieslak & Valor, 2024")
    print("Gap C cieslak year:", "fixed" if (cie is not None and replace_frag(cie, "Cieslak & Valor, 2024", "Cieslak & Valor, 2025", used)) else "not found/skip")
    for marker, old, new in [("Ellstrom et al", "Ellstrom", "Ellström"),
                             ("Holmstrom (2022)", "Holmstrom", "Holmström")]:
        el = find(doc, marker)
        ok = el is not None and replace_frag(el, old, new, used)
        print(f"Gap C spelling {old}->{new}:", "fixed" if ok else "not found/skip")

    shutil.copy(DOCX, BACKUP); doc.save(str(DOCX))
    print(f"\nSaved: {DOCX}\nBackup: {BACKUP}")

if __name__ == "__main__":
    main()
