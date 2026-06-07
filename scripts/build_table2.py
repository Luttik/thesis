# -*- coding: utf-8 -*-
import io

DOC = "unpacked_t2/word/document.xml"

def esc(s):
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = s.replace("'", "&#x2019;")  # apostrophe -> smart quote
    return s

# (descriptive, interpretive, aggregated); "" means continue group above
ROWS = [
    # 4.1 Observing
    ("Observing AI's improvement & potential", "Observing AI progression", "Observing"),
    ("Observing increasing AI adoption", "", ""),
    ("Observing competitor pressure", "Observing market pressure", ""),
    ("Observing changing consumer behavior", "", ""),
    ("Observing the rise of agents of consumers", "", ""),
    ("Observing vendor roadmaps & offerings", "Observing supplier communication", ""),
    # 4.2 Organizational conditions
    ("Resistance to change", "Organizational capacity", "Organizational conditions"),
    ("Limited AI literacy", "", ""),
    ("Lacking systems thinking", "", ""),
    ("Analysis paralysis", "", ""),
    ("Absent innovation culture", "", ""),
    ("Lacking data & infrastructure", "Technical resources", ""),
    ("Lacking technical talent", "", ""),
    ("Strategic direction & vision", "Strategic direction & leadership", ""),
    ("Senior leadership buy-in & backing", "", ""),
    ("Restrictive compliance & legal gatekeeping", "Governance & compliance", ""),
    ("Politics & working in silos", "", ""),
    # 4.2 Steering the organization
    ("Educating & training", "Reshaping conditions", "Steering the organization"),
    ("Experimenting with AI", "", ""),
    ("Bringing people along", "", ""),
    ("Providing clarity", "", ""),
    ("Providing leadership backing", "", ""),
    ("Championing AI", "", ""),
    ("Leveraging data availability", "Leveraging conditions", ""),
    ("Leveraging the right tooling", "", ""),
    ("Leveraging an innovation culture", "", ""),
    ("Leveraging external experts & vendors", "Navigating constraints", ""),
    ("Navigating resistance", "", ""),
    ("Navigating restrictive governance", "", ""),
    # 4.3 Applying agentic AI
    ("Generating insights", "Applying use cases", "Applying agentic AI"),
    ("Creating & validating content & campaigns", "", ""),
    ("Using generic agents", "", ""),
    ("Automating processes", "", ""),
    ("Deploying customer-facing agents", "", ""),
    ("Leveraging tool calling", "Leveraging usage strategies", ""),
    ("Personalizing agents", "", ""),
    # 4.4 Value outcomes
    ("Gaining efficiency & speed", "Gaining benefits", "Value outcomes"),
    ("Gaining scale", "", ""),
    ("Extending the personal skillset", "", ""),
    ("Improving quality of output", "", ""),
    ("Incurring financial costs", "Making sacrifices", ""),
    ("Displacing jobs", "", ""),
    ("Risking hallucination", "Facing risks", ""),
    ("Risking security & privacy violations", "", ""),
    ("Risking brand degradation", "", ""),
]

WIDTHS = [4185, 2430, 2280]

def cell(text, width, header=False):
    border = ('<w:top w:val="single" w:sz="7" w:space="0" w:color="000000"/>'
              '<w:left w:val="nil"/>'
              '<w:bottom w:val="single" w:sz="7" w:space="0" w:color="000000"/>'
              '<w:right w:val="nil"/>') if header else (
              '<w:top w:val="nil"/><w:left w:val="nil"/>'
              '<w:bottom w:val="nil"/><w:right w:val="nil"/>')
    bold = '<w:b/><w:bCs/>' if header else ''
    if text == "":
        run = ('<w:r><w:rPr>%s<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
               '<w:t xml:space="preserve"> </w:t></w:r>' % bold)
    else:
        run = ('<w:r><w:rPr>%s<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
               '<w:t>%s</w:t></w:r>' % (bold, esc(text)))
    return (
        '<w:tc>'
        '<w:tcPr>'
        '<w:tcW w:w="%d" w:type="dxa"/>'
        '<w:tcBorders>%s</w:tcBorders>'
        '<w:tcMar><w:top w:w="0" w:type="dxa"/><w:left w:w="100" w:type="dxa"/>'
        '<w:bottom w:w="0" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tcMar>'
        '</w:tcPr>'
        '<w:p>'
        '<w:pPr><w:spacing w:line="360" w:lineRule="auto"/><w:ind w:firstLine="0"/>'
        '<w:rPr>%s<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:pPr>'
        '%s'
        '</w:p>'
        '</w:tc>'
    ) % (width, border, bold, run)

def row(cells, header=False):
    h = '<w:trHeight w:val="10"/>' if header else '<w:trHeight w:val="270"/>'
    body = ''.join(cell(c, WIDTHS[i], header) for i, c in enumerate(cells))
    return '<w:tr w:rsidR="00401741"><w:trPr>%s</w:trPr>%s</w:tr>' % (h, body)

tbl = []
tbl.append('<w:tbl>')
tbl.append('<w:tblPr>'
           '<w:tblStyle w:val="a2"/>'
           '<w:tblW w:w="8895" w:type="dxa"/>'
           '<w:tblInd w:w="0" w:type="dxa"/>'
           '<w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/>'
           '<w:right w:val="nil"/><w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders>'
           '<w:tblLayout w:type="fixed"/>'
           '<w:tblLook w:val="0600" w:firstRow="0" w:lastRow="0" w:firstColumn="0" '
           'w:lastColumn="0" w:noHBand="1" w:noVBand="1"/></w:tblPr>')
tbl.append('<w:tblGrid><w:gridCol w:w="4185"/><w:gridCol w:w="2430"/><w:gridCol w:w="2280"/></w:tblGrid>')
tbl.append(row(("Descriptive coding", "Interpretive coding", "Aggregated codes"), header=True))
for r in ROWS:
    tbl.append(row(r))
tbl.append('</w:tbl>')
new_table = ''.join(tbl)

# Splice: replace lines 11673..15835 (1-indexed) which span <w:tbl>..</w:tbl>
with io.open(DOC, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Locate the caption paragraph, then the following <w:tbl>..</w:tbl>
cap = next(i for i, l in enumerate(lines) if "Overview of code development" in l)
start = next(i for i in range(cap, len(lines)) if lines[i].strip() == "<w:tbl>")
end = next(i for i in range(start, len(lines)) if lines[i].strip() == "</w:tbl>")

# Sanity: this table must be the code-development table
block = "".join(lines[start:end+1])
assert "Descriptive coding" in block and "Aggregated codes" in block, "wrong table located"

new_lines = lines[:start] + [new_table + "\n"] + lines[end+1:]
with io.open(DOC, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Replaced table at lines %d-%d. New row count (excl header): %d" % (start+1, end+1, len(ROWS)))
