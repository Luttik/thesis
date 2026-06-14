"""Verify the new Table 3 after the open-coding patch.
Dumps the table as it would appear after Accept-All and after Reject-All,
plus shows which author/date each open-coding run carries.
"""
from pathlib import Path
from copy import deepcopy
from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
FN = "Thesis Draft - Daan Luttik - MBA - copy from 2026-06-14.docx"

W_INS = qn("w:ins")
W_DEL = qn("w:del")
W_R = qn("w:r")
W_P = qn("w:p")
W_T = qn("w:t")
W_DELTEXT = qn("w:delText")


def accept_all(tbl):
    el = deepcopy(tbl)
    # remove <w:del> runs/paras entirely; unwrap <w:ins>
    for ins in el.findall(".//" + W_INS):
        parent = ins.getparent()
        idx = list(parent).index(ins)
        for child in list(ins):
            parent.insert(idx, child)
            idx += 1
        parent.remove(ins)
    return el


def text_of_cell(tc):
    parts = []
    for p in tc.iter(W_P):
        runs = []
        for r in p.iter(W_R):
            t = "".join((n.text or "") for n in r.iter(W_T))
            runs.append(t)
        if any(runs):
            parts.append("".join(runs))
    return " / ".join(parts)


doc = Document(str(ROOT / FN))
t = doc.tables[3]._tbl
accepted = accept_all(t)

W_TR = qn("w:tr")
W_TC = qn("w:tc")
print("===== NEW TABLE 3 — AFTER ACCEPT ALL =====")
for ri, tr in enumerate(accepted.findall(W_TR)):
    tcs = tr.findall(W_TC)
    cols = [text_of_cell(tc) for tc in tcs]
    print(f"r{ri}:")
    for ci, c in enumerate(cols):
        print(f"   c{ci}: {c}")

# Author/date audit of the open-coding column runs
print("\n===== OPEN-CODING RUN AUTHORS/DATES (col 0) =====")
for ri, tr in enumerate(t.findall(W_TR)):
    tc = tr.findall(W_TC)[0]
    for ins in tc.findall(".//" + W_INS):
        if ins.find(W_R) is not None:
            auth = ins.get(qn("w:author"))
            date = ins.get(qn("w:date"))
            txt = "".join(n.text or "" for n in ins.iter(W_T))[:40]
            print(f"r{ri}: ins author={auth} date={date} :: {txt}")
