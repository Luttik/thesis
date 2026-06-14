from pathlib import Path
from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
FN = "Thesis Draft - Daan Luttik - MBA - copy from 2026-06-14.docx"
d = Document(str(ROOT / FN))


def cell_text_marked(cell):
    """Return text of a cell, marking ins/del state of each run."""
    parts = []
    tc = cell._tc
    # iterate paragraphs
    for p in tc.findall(".//" + qn("w:p")):
        run_texts = []
        for r in p.findall(qn("w:r")):
            # determine ancestor ins/del
            t = "".join((node.text or "") for node in r.findall(qn("w:t")) + r.findall(qn("w:delText")))
            if not t:
                # delText may be separate
                dt = "".join((node.text or "") for node in r.findall(qn("w:delText")))
                t = dt
            parent = r.getparent()
            tag = parent.tag
            if tag == qn("w:ins"):
                run_texts.append("{INS:" + t + "}")
            elif tag == qn("w:del"):
                run_texts.append("{DEL:" + t + "}")
            else:
                run_texts.append(t)
        # also handle w:ins wrapping w:r directly inside p (already covered since r.getparent is ins)
        if run_texts:
            parts.append("".join(run_texts))
    return " \\n ".join(parts)


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

(ROOT / ".cache" / "table3_tracked.txt").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
