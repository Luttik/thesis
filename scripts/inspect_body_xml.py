# -*- coding: utf-8 -*-
"""Dump pPr of target body paragraphs to match formatting; verify anchors."""
import zipfile
from lxml import etree

DOCX = r"C:\workspace\thesis\Thesis Draft - Daan Luttik - MBA.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
def qn(t): return f"{{{W}}}{t}"

with zipfile.ZipFile(DOCX) as z:
    root = etree.fromstring(z.read("word/document.xml"))

def full_text(p):
    return "".join(t.text or "" for t in p.iter(qn("t")))

# anchors we will use in the patch
anchors_23 = [
    "important bridge between AI capability",
    "If agentic AI is used only to draft emails",
    "Dynamic capabilities theory is particularly useful in this context",
    "These insights suggest three lessons",
    "The digital transformation literature also warns",
]
anchors_511 = [
    "Clear links can be made between the model from Figure 1",
    "First, we go beyond reconfiguration",
    "The study’s distinctive contribution, however, is to show where the binding constraint",
]

paras = list(root.iter(qn("p")))
print("TOTAL paragraphs:", len(paras))

def show_ppr(marker):
    for p in paras:
        if marker in full_text(p):
            pPr = p.find(qn("pPr"))
            ppr_xml = etree.tostring(pPr, pretty_print=True).decode() if pPr is not None else "<none>"
            # strip namespace decls for readability
            print("-" * 70)
            print("ANCHOR OK:", marker[:50])
            print(ppr_xml.split(">", 1)[0][:60], "...")  # opening tag preview
            print(ppr_xml)
            return True
    print("!!! ANCHOR NOT FOUND:", marker)
    return False

print("\n===== 2.3 anchors =====")
for m in anchors_23:
    show_ppr(m)
print("\n===== 5.1.1 anchors =====")
for m in anchors_511:
    show_ppr(m)
