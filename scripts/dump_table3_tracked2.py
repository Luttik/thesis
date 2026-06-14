from pathlib import Path
from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
FN = "Thesis Draft - Daan Luttik - MBA - copy from 2026-06-14.docx"
d = Document(str(ROOT / FN))

W_INS = qn("w:ins")
W_DEL = qn("w:del")
W_R = qn("w:r")
W_P = qn("w:p")
W_T = qn("w:t")
W_DELTEXT = qn("w:delText")


def ancestor_state(r):
    p = r.getparent()
    while p is not None:
        if p.tag == W_INS:
            return "INS"
        if p.tag == W_DEL:
            return "DEL"
        if p.tag == qn("w:tc"):
            return None
        p = p.getparent()
    return None


def cell_text_marked(cell):
    tc = cell._tc
    parts = []
    for p in tc.iter(W_P):
        # skip nested-table paragraphs (none expected here)
        run_strs = []
        for r in p.iter(W_R):
            t = "".join((n.text or "") for n in r.iter(W_T))
            dt = "".join((n.text or "") for n in r.iter(W_DELTEXT))
            txt = t + dt
            if not txt:
                continue
            st = ancestor_state(r)
            if st == "INS":
                run_strs.append("{+}" + txt)
            elif st == "DEL":
                run_strs.append("{-}" + txt)
            else:
                run_strs.append("{=}" + txt)
        if run_strs:
            parts.append("".join(run_strs))
    return " // ".join(parts)


out = []
for ti in (2, 3):
    t = d.tables[ti]
    out.append(f"################ TABLE #{ti}  rows={len(t.rows)} cols={len(t.columns)} ################")
    for ri, row in enumerate(t.rows):
        for ci, c in enumerate(row.cells):
            txt = cell_text_marked(c)
            out.append(f"[{ti}] r{ri} c{ci}: {txt}")
        out.append("  ----")
    out.append("")

(ROOT / ".cache" / "table3_tracked2.txt").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
