# -*- coding: utf-8 -*-
"""Chapter 5 consistency + improvement pass (tracked, author 'Claude').

Aligns the Discussion with the configuration/harness distinction and the new
§4.4.4/Table 4 demonstration; scopes the granular harness claim to participant
articulation. All-or-nothing save."""
from __future__ import annotations
import copy, shutil
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

ROOT      = Path(__file__).resolve().parents[1]
DOCX_PATH = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP    = ROOT / "Thesis Draft - Daan Luttik - MBA.ch5-backup.docx"
AUTHOR = "Claude"; DATE = "2026-06-07T14:00:00Z"
XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"


def _used_ids(doc):
    return {int(el.get(qn("w:id"), 0)) for el in doc.element.body.iter() if el.get(qn("w:id")) is not None}
def _nid(used): n = max(used, default=0) + 1; used.add(n); return n
def full_text(p): return "".join(t.text or "" for t in p.iter(qn("w:t")))
def find_elem(doc, marker):
    for p in doc.paragraphs:
        if marker in full_text(p._element):
            return p._element
    return None

def _ins_run(text, used):
    ins = etree.Element(qn("w:ins")); ins.set(qn("w:id"), str(_nid(used)))
    ins.set(qn("w:author"), AUTHOR); ins.set(qn("w:date"), DATE)
    r = etree.SubElement(ins, qn("w:r")); t = etree.SubElement(r, qn("w:t"))
    t.set(XMLSPACE, "preserve"); t.text = text
    return ins

def replace_fragment_tracked(p_elem, old, new, used):
    runs = p_elem.findall(qn("w:r"))
    segs, total = [], ""
    for r in runs:
        t = r.find(qn("w:t")); txt = t.text if (t is not None and t.text) else ""
        segs.append((r, txt)); total += txt
    start = total.find(old)
    if start < 0:
        return False
    end = start + len(old)
    def mk_run(rPr, s):
        nr = etree.Element(qn("w:r"))
        if rPr is not None: nr.append(copy.deepcopy(rPr))
        tt = etree.SubElement(nr, qn("w:t")); tt.set(XMLSPACE, "preserve"); tt.text = s
        return nr
    def mk_del(rPr, s):
        d = etree.Element(qn("w:del")); d.set(qn("w:id"), str(_nid(used)))
        d.set(qn("w:author"), AUTHOR); d.set(qn("w:date"), DATE)
        dr = etree.SubElement(d, qn("w:r"))
        if rPr is not None: dr.insert(0, copy.deepcopy(rPr))
        dt = etree.SubElement(dr, qn("w:delText")); dt.set(XMLSPACE, "preserve"); dt.text = s
        return d
    pos, inserted = 0, False
    for r, txt in segs:
        r_start, r_end = pos, pos + len(txt); pos = r_end
        if not txt or r_end <= start or r_start >= end:
            continue
        rPr = r.find(qn("w:rPr"))
        ls = max(start, r_start) - r_start; le = min(end, r_end) - r_start
        before, deleted, after = txt[:ls], txt[ls:le], txt[le:]
        parent = r.getparent(); idx = list(parent).index(r)
        parts = []
        if before: parts.append(mk_run(rPr, before))
        if not inserted: parts.append(_ins_run(new, used)); inserted = True
        if deleted: parts.append(mk_del(rPr, deleted))
        if after: parts.append(mk_run(rPr, after))
        for j, part in enumerate(parts): parent.insert(idx + j, part)
        parent.remove(r)
    return inserted


LDQ, RDQ, MD, APO = "“", "”", "—", "’"

# (marker, old, new) -------------------------------------------------------- #
EDITS = [
    # [311] tighten the lead-in
    ("those who help them implement their AI strategy",
     "and shows how marketing managers can create value using agentic AI.",
     "reconstructing how that value is created in practice."),
    # [312] add pointer to the demonstration
    ("were reported to produce different outcomes across organizations",
     "produce different outcomes across organizations.",
     "produce different outcomes across organizations (Section 4.4.4; Table 4)."),
    # [312] drop harness gloss + unneeded hedge (broad claim now demonstrated)
    ("were reported to produce different outcomes across organizations",
     f"and, where participants could articulate it, the configuration (the {LDQ}harness{RDQ}) in which the technology was applied",
     "and the configuration in which the technology was applied"),
    # [316] anchor 'what separated organizations' to Table 4
    ("Extending dynamic capabilities to agentic AI",
     "providing clarity, and protecting experimentation. This relocates the locus",
     "providing clarity, and protecting experimentation; the divergent outcomes for comparable "
     "use cases make this difference visible (Section 4.4.4; Table 4). This relocates the locus"),
    # [317] distinguish configuration (broad) from harness (agent-level); scope; cite Table 4
    ("Value as configuration-in-use rather than capability",
     "it is produced by the complete harness around the model — the data it can reach, its memory, "
     "the tools it can call, the guardrails, the prompt, and the choice of model (Sections 4.3.2 and 4.4). "
     "Because outcomes for nominally identical use cases diverged with this configuration, value cannot "
     "be read off the technology;",
     f"it is produced not by the model but by the wider configuration in which the model is embedded {MD} "
     f"the organizational conditions and processes around it, together with the agent{APO}s own harness: "
     f"the data it can reach, its memory, the tools it can call, the guardrails, the prompt, and the choice "
     f"of model (Sections 4.3.2 and 4.4.4). The harness was the component that participants who could "
     f"articulate the mechanism named most directly. Because outcomes for nominally identical use cases "
     f"diverged with this configuration (Table 4), value cannot be read off the technology;"),
]


def main():
    doc = Document(str(DOCX_PATH)); used = _used_ids(doc)
    results = []
    for marker, old, new in EDITS:
        el = find_elem(doc, marker)
        if el is None:
            results.append((marker[:40], "PARA NOT FOUND")); continue
        ok = replace_fragment_tracked(el, old, new, used)
        results.append((marker[:40], "ok" if ok else "FRAGMENT NOT MATCHED"))
    print("Edit results:")
    for m, s in results: print(f"  [{s:>18}]  {m}")
    if all(s == "ok" for _, s in results):
        shutil.copy(DOCX_PATH, BACKUP); doc.save(str(DOCX_PATH))
        print(f"\nAll applied. Saved: {DOCX_PATH}\nBackup: {BACKUP}")
    else:
        print("\nNOT SAVED - a fragment failed to match; file untouched.")


if __name__ == "__main__":
    main()
