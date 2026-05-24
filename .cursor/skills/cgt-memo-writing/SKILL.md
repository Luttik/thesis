---
name: cgt-memo-writing
description: >
  Write analytical memos following Charmaz's (2006) memo-writing practices. Supports
  three memo types: code memos (define a code), theoretical memos (develop a concept),
  and operational memos (log methodological decisions). Memos are written to
  qdpx-coding/memos.md and exported back to QDPX. Use when the user wants to
  write a memo, explore a theoretical idea, compare codes, or document an analytical
  decision.
---

# CGT Memo Writing Skill

## Purpose

Write **analytical memos** as described in Charmaz (2006, Ch. 3): the essential
thinking-on-paper that moves the researcher from descriptive codes toward theoretical
categories. Memos are not summaries — they are exploratory, comparative, and
hypothesis-generating. They record the researcher's thinking in process, including
uncertainty and contradiction.

**Always use this skill in combination with the QDPX skill.** Read
`.cursor/skills/qdpx/SKILL.md` first to understand the import/export mechanics
and file formats before proceeding.

---

## Three Memo Types (Charmaz 2006)

### Code Memo
Defines a single code in depth. Written when a code is new, ambiguous, or has
emerged as analytically important. Answers: what exactly does this code capture,
and where are its boundaries?

### Theoretical Memo
Develops a conceptual idea that has emerged from comparing codes. Written when
the researcher notices a pattern, tension, or possible relationship between codes
that suggests something theoretical. Answers: what might this mean? what would
it imply if X relates to Y? what question does this raise for further data collection?

### Operational Memo
Logs a methodological decision — why a code was merged, why a document was
prioritised, why a theoretical sampling choice was made. Answers: what did I do,
why did I do it, and what are the implications for the analysis?

---

## Workflow

### Step 1 — Import QDPX workspace snapshot

Run the import:
1. `python .cursor/skills/qdpx/qdpx_import.py --qdpx "Thesis.qdpx" --out qdpx-coding`

### Step 2 — Read context

Before writing any memo, read:
1. `qdpx-coding/memos.md` — avoid duplicating an existing memo; extend or reference it instead
2. `qdpx-coding/codebook.md` — the current codes and their descriptions
3. The relevant `qdpx-coding/quotations/[Doc].md` file(s) — the actual data passages
   that are prompting this memo

### Step 3 — Determine memo type and topic

Ask the researcher (or infer from context):
- **What prompted this memo?** (a new code, a surprising pattern, a merge decision?)
- **Which memo type fits best?** (code / theoretical / operational)
- **Which codes or quotations are central to it?**

If the researcher asks for a memo but does not specify a type, suggest the most
appropriate type with a brief rationale and proceed unless they redirect.

### Step 4 — Write the memo

Use the following templates. Append the new memo at the end of `qdpx-coding/memos.md`
**without** an `<!-- id: HEX -->` anchor — the export script assigns IDs to new memos.

#### Code Memo template

```markdown
## Code Memo: [Code Name]

**Type**: Code memo  
**Date**: YYYY-MM-DD  
**Code**: `[Code Name]`

**Definition**: [1–2 sentences: what action does this code capture?]

**Boundaries**:
- Includes: [what fits]
- Excludes: [what does not fit — especially contrast with the most similar code]

**In vivo anchor**: "[participant quote that best exemplifies this code]"
— *[Document name]*

**Constant comparison**:
Compare this code with `[Most Similar Code]`: [how are they alike / different?]
Compare this code with `[Contrasting Code]`: [what does the contrast reveal?]

**Open question**: [One question this code raises that future data or memos should address]
```

#### Theoretical Memo template

```markdown
## Theoretical Memo: [Title — state the idea, not just the topic]

**Type**: Theoretical memo  
**Date**: YYYY-MM-DD  
**Central codes**: `[Code A]`, `[Code B]`

**Observation**: [What pattern, tension, or relationship prompted this memo?
Be specific — cite segment numbers or quotation IDs where relevant.]

**Hypothesis**: [A tentative claim. Use "may", "seems to", "raises the question
whether" — this is exploratory, not conclusive.]

**Constant comparison**:
[Compare the codes or patterns across at least two documents or participants.
What varies? What holds constant?]

**Implications for theory**: [What would this mean for the emerging theoretical
account if the hypothesis holds?]

**Implications for sampling**: [What data would confirm, challenge, or refine
this hypothesis? Who should be interviewed next, or what passages should be
re-examined?]

**Contradictions**: [Any evidence in the data that cuts against this hypothesis.
Do not suppress contradictions — they are analytically productive.]
```

#### Operational Memo template

```markdown
## Operational Memo: [Decision being documented]

**Type**: Operational memo  
**Date**: YYYY-MM-DD

**Decision**: [What was done? State it plainly.]

**Rationale**: [Why? What analytical logic or data evidence drove this decision?]

**Alternatives considered**: [What other options were weighed and why they were
set aside.]

**Implications**: [How does this decision affect subsequent coding, sampling,
or theory building?]

**Reversibility**: [Can this be undone if it turns out to be wrong? How?]
```

### Step 5 — Apply the constant-comparative method

Every memo — regardless of type — should include at least one comparison. Charmaz
(2006) is clear: memos without comparison are notes, not analysis. The comparison
can be:
- Code vs. code ("how does X differ from Y?")
- Code vs. data ("does this code hold when I look at [other document]?")
- This participant vs. another ("participant A resists X while participant B
  embraces it — what explains the difference?")
- Current hypothesis vs. earlier hypothesis ("I thought X was central, but now Y
  seems more generative — why did I change my view?")

### Step 6 — Review before export

Present the memo text to the researcher before writing it to disk:
1. Show the full memo as it will appear in `qdpx-coding/memos.md`.
2. Ask: "Does this capture what you wanted to explore? Any changes before I save?"

After approval, append the memo to `qdpx-coding/memos.md`.

### Step 7 — Export, validate, and diff (QDPX workflow)

1. Run export: `python .cursor/skills/qdpx/qdpx_export.py --base "Thesis.qdpx" --in qdpx-coding --out "Thesis-updated.qdpx"`
2. Validate no-loss: `python .cursor/skills/qdpx/qdpx_validate.py --baseline "Thesis.qdpx" --qdpx "Thesis-updated.qdpx"`
3. Review deltas: `python .cursor/skills/qdpx/qdpx_diff.py --old "Thesis.qdpx" --new "Thesis-updated.qdpx"`
4. Confirm the memo title is present after re-import: `python .cursor/skills/qdpx/qdpx_import.py --qdpx "Thesis-updated.qdpx" --out qdpx-coding-verify`

---

## Memo-writing principles (Charmaz 2006)

- **Write early and often.** A memo written on the first read of a document is
  more analytically generative than one written after everything is already coded.
- **Write to think, not to report.** The purpose is to push thinking forward, not
  to summarise what is already known. If a memo contains no new idea, it is a note,
  not a memo.
- **Be speculative.** Use tentative language ("I wonder if...", "this may suggest...",
  "what if..."). Memos are not claims — they are questions.
- **Follow a lead.** If one idea in a memo opens up into a bigger question, start
  a new memo rather than expanding the current one indefinitely.
- **Memos inform theoretical sampling.** Every memo should leave the researcher with
  a question that could be answered by seeking out more data.

---

## What memo writing is NOT

- Not a summary of what was already coded — if you are restating what the quotations
  say, you are not writing a memo.
- Not a final argument — memos are working documents; they can be wrong.
- Not a transcript excerpt — memos draw on quotations but are written in the
  researcher's analytical voice.

---

## Key Paths

| Item | Path |
|---|---|
| QDPX skill | `.cursor/skills/qdpx/SKILL.md` |
| Memos | `qdpx-coding/memos.md` |
| Codebook | `qdpx-coding/codebook.md` |
| Quotations | `qdpx-coding/quotations/` |
