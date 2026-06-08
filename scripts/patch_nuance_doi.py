# -*- coding: utf-8 -*-
"""
- Clean: fold the tempered-disruption signal ("faster same" vs "different and
  better") into §5.2.2, and the junior inversion + Brynjolfsson finding into §5.1.6.
- Tracked: fix the Vidal et al. DOI typo (…07.0200 -> …07.020), author "Claude".
"""
from __future__ import annotations

import copy, shutil
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

from patch_sec44_inside_out import find_elem, insert_before, XMLSPACE, _used_ids
from patch_sec51_discussion import clean_body
from patch_sec23_dc_value import _stamp

P = Path(r"C:\workspace\thesis\Thesis Draft - Daan Luttik - MBA.docx")

S522 = (
    "The findings imply a strategic choice between two postures. Much adoption is "
    "essentially AI hygiene — executing proven use cases efficiently to reach parity — and "
    "because competitors will inevitably pursue the same efficiency gains, these are "
    "unlikely to confer durable advantage; indeed, where every firm adopts similar systems "
    "the result can be a homogenization of output that erodes distinctiveness (Doshi & "
    "Hauser, 2024). Pursuing outsized returns instead requires differentiation: finding "
    "novel use cases, experimenting to learn what works, and assembling the skills to "
    "implement them well — the strategic, rather than merely operational, register of value "
    "(Section 2.3). The data suggest the default drift runs toward following rather than "
    "differentiating: participants reported abundant efficiency gains — doing the “faster "
    "same” — but comparatively little vision for the “different and better” applications "
    "that genuine differentiation requires (Section 4.1). Neither posture is inherently "
    "wrong, but they demand different investments, and because the pull is toward parity, "
    "managers should choose consciously rather than drift; for a structurally resistant "
    "organization, even disciplined following may be the value-maximizing option."
)

S516_JR = (
    "One outcome, however, resists this containment and points beyond the firm. Deploying "
    "agentic AI first on junior tasks threatens the pipeline through which juniors become "
    "seniors (Section 4.5.4), and the threat is sharpened by an inversion the data record: "
    "the juniors whose work is most exposed are often the most AI-native, more fluent with "
    "the tools than the senior practitioners who lead — a pattern consistent with evidence "
    "that the productivity gains from generative AI accrue most to less-experienced workers "
    "(Brynjolfsson et al., 2025). Thinning that layer trades a near-term operational gain "
    "for a longer-term erosion of capability that no efficiency metric records. This "
    "tension between operational and strategic value, like the emergence of "
    "consumers’ own agents as a new intermediary, is not resolved within the present data "
    "and is taken up again as a direction for future research in Section 5.3."
)


def replace_clean(doc, anchor, text):
    el = find_elem(doc, anchor); assert el is not None, anchor
    insert_before(el, [clean_body(text)]); el.getparent().remove(el)


def fix_vidal_doi_tracked(doc):
    used = _used_ids(doc)
    vid = find_elem(doc, "Vidal, J. F., Perotti")
    assert vid is not None, "Vidal entry not found"
    tgt = next((t for t in vid.iter(qn("w:t")) if t.text and "jbusres.2022.07.0200" in t.text), None)
    assert tgt is not None, "Vidal DOI run not found"
    run = tgt.getparent()
    tgt.text = tgt.text.replace("jbusres.2022.07.0200", "jbusres.2022.07.020")
    d = etree.Element(qn("w:del")); _stamp(d, used)
    r = etree.SubElement(d, qn("w:r"))
    rpr = run.find(qn("w:rPr"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    dt = etree.SubElement(r, qn("w:delText")); dt.set(XMLSPACE, "preserve"); dt.text = "0"
    run.addnext(d)


def main():
    shutil.copy(P, P.with_name("Thesis Draft - Daan Luttik - MBA.nuance-backup.docx"))
    doc = Document(str(P))
    replace_clean(doc, "The findings imply a strategic choice between two postures", S522)
    print("1. §5.2.2: tempered-disruption (faster-same vs different-and-better) folded in")
    replace_clean(doc, "One outcome, however, resists this containment", S516_JR)
    print("2. §5.1.6: junior inversion + Brynjolfsson finding folded in")
    fix_vidal_doi_tracked(doc)
    print("3. Vidal DOI: tracked fix …07.0200 -> …07.020")
    doc.save(str(P))
    print("saved")


if __name__ == "__main__":
    main()
