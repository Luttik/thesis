"""Replace the open-coding column (col 0) of the NEW Table 3 (table index 3,
the pending <w:ins> realigned coding table) with the OLD table's open codes
(verbatim), redistributed to match the new focused + theoretical rows.

The new table is a single pending tracked insertion by "Claude". We refine that
insertion: in each data row's first cell we drop the existing inserted content
runs and insert one new <w:ins> run carrying the old open codes, dated today so
the change is traceable in the review pane. Focused + theoretical columns are
left untouched.
"""
from pathlib import Path
import shutil
from xml.sax.saxutils import escape

from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import qn, nsdecls

ROOT = Path(__file__).resolve().parents[1]
FN = "Thesis Draft - Daan Luttik - MBA - copy from 2026-06-14.docx"
SRC = ROOT / FN
BACKUP = ROOT / (FN.replace(".docx", "-backup.docx"))

DATE = "2026-06-14T12:00:00Z"
AUTHOR = "Claude"

# Old open codes (verbatim from old Table 3), mapped onto the new 12-row layout.
# key = data-row index in the new table (row 0 is the header row).
NEW_OPEN = {
    1: "AI’s improvement & potential; Observing increasing AI adoption; vendor roadmaps & offerings",
    2: "Competitor pressure; Changing consumer behavior; The rise of agents of consumers",
    3: ("Resistance to change; Limited AI literacy; Lacking systems thinking; "
        "Analysis paralysis; Absent innovation culture; Strategic direction & vision; "
        "Senior leadership buy-in & backing; Educating & training; Experimenting with AI; "
        "Bringing people along; Providing clarity; Providing leadership backing; "
        "Championing AI; Leveraging an innovation culture; Navigating resistance"),
    4: ("Lacking data & infrastructure; Lacking technical talent; "
        "Leveraging data availability; Leveraging the right tooling; "
        "Leveraging external experts & vendors"),
    5: "Restrictive compliance & legal gatekeeping; Politics & working in silos; Navigating restrictive governance",
    6: "Generating insights",
    7: "Creating & validating content & campaigns",
    8: "Using generic agents; Automating processes; Leveraging tool calling; Personalizing agents",
    9: "Deploying customer-facing agents",
    10: "Gaining efficiency & speed; Gaining scale; Extending the personal skillset; Improving quality of output",
    11: "Incurring financial costs; Displacing jobs",
    12: "Risking hallucination; Risking security & privacy violations; Risking brand degradation",
}

W_P = qn("w:p")
W_PPR = qn("w:pPr")
W_INS = qn("w:ins")
W_DEL = qn("w:del")
W_R = qn("w:r")


def build_ins(text, wid):
    xml = (
        f'<w:ins {nsdecls("w")} w:id="{wid}" w:author="{AUTHOR}" w:date="{DATE}">'
        f'<w:r><w:rPr><w:rFonts w:cs="Segoe UI"/><w:color w:val="0A0A0A"/>'
        f'<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
        f'<w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:ins>'
    )
    return parse_xml(xml)


def main():
    shutil.copyfile(SRC, BACKUP)
    print(f"backup -> {BACKUP.name}")

    doc = Document(str(SRC))
    t = doc.tables[3]
    assert len(t.rows) == 13, f"expected 13 rows, got {len(t.rows)}"

    wid = 90000
    for ri in range(1, 13):
        cell = t.rows[ri].cells[0]
        tc = cell._tc
        paras = tc.findall(W_P)
        assert paras, f"row {ri}: no paragraph in cell"
        p = paras[0]
        # Remove existing content runs (direct-child <w:ins>/<w:del>/<w:r>) but keep <w:pPr>.
        for child in list(p):
            if child.tag in (W_INS, W_DEL, W_R):
                p.remove(child)
        # Insert the new tracked run after pPr (or at start if no pPr).
        new_ins = build_ins(NEW_OPEN[ri], wid)
        wid += 1
        ppr = p.find(W_PPR)
        if ppr is not None:
            ppr.addnext(new_ins)
        else:
            p.insert(0, new_ins)
        # Drop any extra paragraphs beyond the first (none expected).
        for extra in paras[1:]:
            tc.remove(extra)
        print(f"row {ri}: set open coding ({len(NEW_OPEN[ri])} chars)")

    doc.save(str(SRC))
    print("saved.")


if __name__ == "__main__":
    main()
