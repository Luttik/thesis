# -*- coding: utf-8 -*-
"""Dry-run: check each prepared minimal-fix OP against the CURRENT saved doc.
Read-only. Reports which fixes still apply vs. are outdated/already done."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from docx import Document
from patch_minimal_fixes import OPS, find_para, visible_text, DOCX

doc = Document(str(DOCX))

def chk(anchor, old, new, style):
    p = find_para(doc, anchor, style)
    if p is None:
        return "ANCHOR-GONE"
    vt = visible_text(p)
    if old in vt:
        return "APPLIES"          # old text present -> fix still needed
    if new in vt:
        return "ALREADY-DONE"     # already matches target
    return "OLD-CHANGED"          # paragraph exists but old string no longer there

print(f"{'STATUS':14} {'GROUP':9} LABEL")
print("-"*70)
counts = {}
for anchor, old, new, label, group, style in OPS:
    s = chk(anchor, old, new, style)
    counts[s] = counts.get(s, 0) + 1
    print(f"{s:14} {group:9} {label}")
print("-"*70)
print("summary:", counts)
