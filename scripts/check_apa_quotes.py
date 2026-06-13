"""
Check APA quote-length rules in the thesis DOCX.

APA 7 rule: quotations of 40 words OR MORE -> block quote (its own indented
paragraph, no quotation marks). Fewer than 40 words -> inline, wrapped in
quotation marks.

This script flags two kinds of likely mistakes:
  A) Block quotes (style "Quote") that are SHORTER than 40 words
     -> candidate for inlining.
  B) Inline quoted spans (curly/straight double quotes inside body paragraphs)
     that are 40 words OR MORE -> candidate for block-quoting.

Tracked changes: insertions are counted (accepted view), deletions excluded.
Consecutive "Quote" paragraphs are grouped into a single logical block quote.
"""
import sys
import docx
from docx.oxml.ns import qn

PATH = sys.argv[1] if len(sys.argv) > 1 else "artifacts/_quotecheck.docx"
THRESHOLD = 40

OPEN_Q = "“"   # left double quote
CLOSE_Q = "”"  # right double quote
STRAIGHT = '"'

d = docx.Document(PATH)


def accepted_text(pel):
    """Concatenate visible text: include w:ins, exclude w:del."""
    parts = []
    for t in pel.iter(qn("w:t")):
        anc = t.getparent()
        skip = False
        while anc is not None:
            if anc.tag == qn("w:del"):
                skip = True
                break
            anc = anc.getparent()
        if not skip:
            parts.append(t.text or "")
    return "".join(parts)


def wc(s):
    return len(s.split())


paras = [(i, p, p.style.name, accepted_text(p._p)) for i, p in enumerate(d.paragraphs)]

# ---------------------------------------------------------------------------
# A) Block quotes (Quote style), grouped into consecutive runs
# ---------------------------------------------------------------------------
print("=" * 78)
print("A) BLOCK QUOTES (style='Quote') and their word counts")
print("    flag = SHORTER than %d words -> consider making inline" % THRESHOLD)
print("=" * 78)

groups = []
cur = None
for i, p, sty, txt in paras:
    if sty == "Quote":
        if cur and cur["end"] == i - 1:
            cur["end"] = i
            cur["text"] += " " + txt
        else:
            cur = {"start": i, "end": i, "text": txt}
            groups.append(cur)
    else:
        cur = None

short_blocks = []
for g in groups:
    n = wc(g["text"])
    flag = "  <-- SHORT (under %d)" % THRESHOLD if n < THRESHOLD else ""
    if g["start"] == g["end"]:
        loc = "para %d" % g["start"]
    else:
        loc = "paras %d-%d (multi)" % (g["start"], g["end"])
    print(f"  {loc:22s} wc={n:3d}{flag}")
    if n < THRESHOLD:
        short_blocks.append((g, n))

print("\n  --- %d short block quote(s) flagged ---" % len(short_blocks))
for g, n in short_blocks:
    print(f"\n  [paras {g['start']}-{g['end']}] wc={n}")
    print("   " + g["text"][:400])

# ---------------------------------------------------------------------------
# B) Inline quoted spans in body paragraphs >= 40 words
# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print("B) INLINE QUOTED SPANS (in non-Quote paragraphs) >= %d words" % THRESHOLD)
print("    flag = should probably be a BLOCK quote")
print("=" * 78)


def find_quoted_spans(text):
    """Return list of quoted substrings using curly pairs and straight pairs."""
    spans = []
    # curly pairs
    idx = 0
    while True:
        a = text.find(OPEN_Q, idx)
        if a == -1:
            break
        b = text.find(CLOSE_Q, a + 1)
        if b == -1:
            break
        spans.append(text[a + 1:b])
        idx = b + 1
    # straight double-quote pairs (even/odd)
    positions = [j for j, ch in enumerate(text) if ch == STRAIGHT]
    for k in range(0, len(positions) - 1, 2):
        a, b = positions[k], positions[k + 1]
        spans.append(text[a + 1:b])
    return spans


long_inline = []
near_inline = []
for i, p, sty, txt in paras:
    if sty == "Quote":
        continue
    for span in find_quoted_spans(txt):
        n = wc(span)
        if n >= THRESHOLD:
            long_inline.append((i, sty, n, span))
        elif n >= 30:
            near_inline.append((i, sty, n, span))

for i, sty, n, span in long_inline:
    print(f"\n  [para {i}] style={sty} wc={n}  <-- LONG inline quote")
    print("   " + span[:500])

print("\n  --- %d long inline quote(s) flagged (>=%d words) ---" % (len(long_inline), THRESHOLD))

print("\n  Borderline inline quotes (30-39 words) worth a manual look:")
for i, sty, n, span in near_inline:
    print(f"   [para {i}] wc={n}: {span[:120]}")

# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print("SUMMARY")
print("=" * 78)
print("  block quotes total ............. %d" % len(groups))
print("  block quotes UNDER 40 words .... %d  (candidates to inline)" % len(short_blocks))
print("  inline quotes >= 40 words ...... %d  (candidates to block-quote)" % len(long_inline))
print("  inline quotes 30-39 words ...... %d  (borderline)" % len(near_inline))
