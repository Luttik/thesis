# -*- coding: utf-8 -*-
"""
Tracked additions to Chapter 2 (author "Claude"), seeding the lenses the
discussion leans on, plus the Enholm year fix:
  - §2.4: a dynamic-capabilities paragraph (Teece 1997/2007; Hanelt 2021).
  - §2.3: a value-co-creation + practice-lens passage (Vargo & Lusch 2017;
    Kaartemo & Helkkula 2018; Leone 2021; Orlikowski 2000).
  - §5.1.1: "Enholm et al. (2021)" -> "(2022)" in two places (citation matches
    the reference list; the unrelated "the AI of 2021" is left untouched).
All sources are already in the reference list.
"""
from __future__ import annotations

import copy, shutil
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

from patch_sec44_inside_out import find_elem, insert_before, XMLSPACE, _used_ids
from patch_sec51_discussion import ins_body_nocolor
from patch_sec23_dc_value import _stamp

P = Path(r"C:\workspace\thesis\Thesis Draft - Daan Luttik - MBA.docx")

S_DC = (
    "These managerial roles are given a sharper theoretical foundation by the "
    "dynamic-capabilities perspective. Teece et al. (1997) define dynamic capabilities as a "
    "firm’s ability to integrate, build, and reconfigure internal and external competences "
    "in response to a changing environment, and Teece (2007) disaggregates them into the "
    "microfoundations of *sensing* opportunities, *seizing* them, and *transforming* "
    "(reconfiguring) the resource base, coordinated through what he terms *asset "
    "orchestration*. This framework has already been carried into the digital-transformation "
    "field, where Hanelt et al. (2021) describe the more malleable organizational designs "
    "that continuous digital adaptation demands, though it is typically applied at the level "
    "of the firm rather than the individual manager. It offers a useful lens for agentic AI "
    "because it frames value creation as an act of managerial capability — sensing where the "
    "technology applies, seizing the opportunity by building the conditions for it, and "
    "reconfiguring how work is organized around it — exercised in response to an external "
    "technological shift; Section 5.1 develops this mapping from the empirical data."
)

S_CC1 = (
    "Value is also not delivered by a firm to a passive recipient but co-created. "
    "Service-dominant logic holds that value emerges through the integration of resources "
    "among actors, with operant resources — knowledge and skills applied to other resources "
    "— as the true source of advantage (Vargo & Lusch, 2017). Within this view, AI is "
    "increasingly understood not as a passive instrument but as an active participant in "
    "value co-creation: Kaartemo and Helkkula’s (2018) review positions AI and robots as "
    "actors in the co-creation process, and Leone et al. (2021) show AI enabling and "
    "enhancing co-creation among providers, customers, and end users in industrial markets. "
    "This perspective grows more relevant as consumers begin to act through their own AI "
    "agents, introducing a new actor into the exchange."
)

S_CC2 = (
    "A complementary insight comes from the practice-based tradition: a technology’s "
    "structures and effects are not fixed in the artifact but emergent in its use, enacted "
    "as people draw on it in practice (Orlikowski, 2000). Taken together, these perspectives "
    "frame an agentic system’s value as something enacted through how it is configured and "
    "used within a web of actors, and they distinguish the value created in use from the "
    "value a firm ultimately captures as advantage."
)


def tracked_sub(doc, para_anchor, run_contains, old, new, used):
    p = find_elem(doc, para_anchor)
    assert p is not None, para_anchor
    t = next((x for x in p.iter(qn("w:t"))
              if x.text and run_contains in x.text and old in x.text), None)
    assert t is not None, (para_anchor, run_contains)
    T = t.text; i = T.find(old)
    pre, post = T[:i], T[i + len(old):]
    run = t.getparent(); rpr = run.find(qn("w:rPr"))

    def mkrun(text):
        r = etree.Element(qn("w:r"))
        if rpr is not None:
            r.append(copy.deepcopy(rpr))
        tt = etree.SubElement(r, qn("w:t")); tt.set(XMLSPACE, "preserve"); tt.text = text
        return r

    t.text = pre
    d = etree.Element(qn("w:del")); _stamp(d, used)
    dr = etree.SubElement(d, qn("w:r"))
    if rpr is not None:
        dr.append(copy.deepcopy(rpr))
    dt = etree.SubElement(dr, qn("w:delText")); dt.set(XMLSPACE, "preserve"); dt.text = old
    ins = etree.Element(qn("w:ins")); _stamp(ins, used); ins.append(mkrun(new))
    run.addnext(mkrun(post)); run.addnext(ins); run.addnext(d)


def main():
    shutil.copy(P, P.with_name("Thesis Draft - Daan Luttik - MBA.sec2-backup.docx"))
    doc = Document(str(P)); used = _used_ids(doc)

    # 1. §2.4 dynamic-capabilities paragraph (before the Gebauer paragraph)
    insert_before(find_elem(doc, "Gebauer et al. (2020) describe a concerning pattern"),
                  [ins_body_nocolor(S_DC, used)])
    print("1. §2.4: dynamic-capabilities paragraph inserted (tracked)")

    # 2. §2.3 co-creation + practice-lens passage (at the end of §2.3, before the §2.4 heading)
    insert_before(find_elem(doc, "Learnings from earlier waves of digital transformation"),
                  [ins_body_nocolor(S_CC1, used), ins_body_nocolor(S_CC2, used)])
    print("2. §2.3: co-creation + practice-lens passage inserted (tracked)")

    # 3. §5.1.1 Enholm (2021) -> (2022), two places
    tracked_sub(doc, "In line with earlier work on digital transformation by Enholm",
                "2021)", "2021", "2022", used)
    tracked_sub(doc, "Where Enholm et al. (2021) still note governance",
                "Where Enholm et al.", "2021", "2022", used)
    print("3. §5.1.1: Enholm (2021) -> (2022) in two places (tracked)")

    doc.save(str(P))
    print("saved")


if __name__ == "__main__":
    main()
