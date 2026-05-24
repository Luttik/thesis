---
name: cgt-initial-coding
description: >
  Apply Charmaz's (2006) initial/open coding to a single interview transcript in the QDPX workspace.
  Guides line-by-line, gerund-based coding with preference for existing codes and in vivo
  language. Includes a mandatory researcher review before export. Use when the user wants
  to code a new document, do open coding, or start the first pass on a transcript.
---

# CGT Initial Coding Skill

## Purpose

Perform **initial coding** as described in Charmaz (2006, Ch. 2): a close, line-by-line
 reading of a transcript that codes actions and processes, staying near the participants'
 own language. This skill recodes and refines existing quotations in `qdpx-coding/quotations/`
 and writes a code memo for any genuinely new code introduced.

**Always use this skill in combination with the QDPX skill.** Read
`.cursor/skills/qdpx/SKILL.md` first to understand the import/export mechanics
and file formats before proceeding.

---

## Workflow

### Step 1 — Import QDPX workspace snapshot

Run the import:
1. `python .cursor/skills/qdpx/qdpx_import.py --qdpx "Thesis.qdpx" --out qdpx-coding`

### Step 2 — Read context

Read in this order:
1. `qdpx-coding/codebook.md` — internalize the full list of existing codes
2. `qdpx-coding/quotations/[Target Doc].md` — see what has already been coded in this document
3. `qdpx-coding/documents/[Target Doc].md` — the full interview text for contextual reading

### Step 3 — Recode quotation by quotation

Work through each quotation in `qdpx-coding/quotations/[Target Doc].md`. For each quotation,
adjust the `**Codes**:` line to keep, remove, or add codes based on initial-coding principles.

Note: creating brand-new quotations is currently not part of the QDPX exporter workflow in
this repo. When you find uncaptured passages, document them in an operational memo and handle
new quote creation in the Atlas fallback path only if explicitly required.

**CGT initial coding principles (Charmaz 2006):**
- **Use gerunds** — code what people are *doing*, not what they *are*. Prefer
  "experiencing tension" over "tension", "negotiating adoption" over "adoption barrier".
- **Stay close to the data** — use the participant's own words where possible
  (in vivo codes). If a participant says "we had to fight for every inch of budget",
  a good code is "fighting for budget approval".
- **Code actions and processes** — ask "what is happening here?" and "what is this
  person doing?".
- **Short and active** — codes should be readable as a phrase, not a sentence.
- **One code per action** — a passage can receive multiple codes if it captures
  multiple distinct actions, but do not force a single code to carry two meanings.

**Reuse before creating:**
1. Check `codebook.md` for an existing code that fits. If one fits well, use it — even
   if it was not previously used on this document.
2. If no existing code fits, create a new code. Name it as a gerund phrase. Write a
   brief code memo for it (see Step 4). New codes referenced in `**Codes**:` lines
   are created in the QDPX code tree by the exporter.
3. If an existing code is close but not quite right, note this as a candidate for
   renaming in focused coding — do not rename it now.

**Edit using the QDPX quotations format:**
```markdown
## Quotation N
<!-- id: ... -->
**Codes**: `Existing Code Name`, `Another Code`

> Existing quotation text (read-only)
```

Rules:
- Edit only the `**Codes**:` line for each quotation.
- Keep `<!-- id: ... -->` and `<!-- span: start:end -->` anchors unchanged.
- Code names must match `codebook.md` headings exactly (capitalisation, punctuation).
- Treat quote text as read-only context.

### Step 4 — Write memos as you code (do not wait until the end)

Memo writing is not a separate phase — it interrupts coding whenever something
analytically interesting surfaces. Use the `cgt-memo-writing` skill templates for
all memos and append them to `qdpx-coding/memos.md` immediately.

**Write a code memo when:**
- A new code is introduced (mandatory — define it before moving to the next segment)
- An existing code feels like it is being stretched to cover something slightly
  different (flag the boundary tension)

**Write a theoretical memo when:**
- A participant says something that contradicts an earlier participant on the same
  action — note the variation and what it might mean
- Two codes keep appearing on the same segments — ask why they travel together
- A passage surprises you or cuts against an emerging assumption — follow the lead
  immediately, even mid-document

**Write an operational memo when:**
- You choose to leave a segment uncoded and the reason is non-obvious
- You apply an existing code but it feels like a poor fit — note it as a candidate
  for splitting or renaming in focused coding

**Minimal code memo for a new code** (use the full template from `cgt-memo-writing`
skill for important codes; this shorthand is acceptable for minor initial codes):

```markdown
## Code Memo: [New Code Name]

**Type**: Code memo  
**Date**: YYYY-MM-DD

**Definition**: What this code captures. One or two sentences.  
**Boundaries**: What it does NOT cover (contrast with the most similar existing code).  
**In vivo source**: Quote the participant phrase that prompted this code.  
**Candidate for focused coding**: Yes / No — brief reason.
```

When a theoretical memo is triggered mid-coding, write it immediately, then return
to the segment where you left off. Do not defer it — the insight will be weaker
if reconstructed later.

### Step 5 — Review before export (mandatory)

Before running the export, present the following to the researcher:

1. **Updated quotations summary** — a list of quotations whose `**Codes**:` line changed,
   showing quotation number, old codes, new codes.
2. **New codes introduced** — list of any code names that do not appear in
   `codebook.md` and will be created during export.
3. **Uncaptured passage notes** — any important passages not represented by existing quotations.

Wait for explicit researcher approval ("yes", "go ahead", or similar) before exporting.
If the researcher says "edit X" or "no", make the requested changes and re-present
the summary.

### Step 6 — Export, validate, and diff (QDPX workflow)

After approval:
1. Run export: `python .cursor/skills/qdpx/qdpx_export.py --base "Thesis.qdpx" --in qdpx-coding --out "Thesis-updated.qdpx"`
2. Validate no-loss: `python .cursor/skills/qdpx/qdpx_validate.py --baseline "Thesis.qdpx" --qdpx "Thesis-updated.qdpx"`
3. Review deltas: `python .cursor/skills/qdpx/qdpx_diff.py --old "Thesis.qdpx" --new "Thesis-updated.qdpx"`
4. Re-import for spot check: `python .cursor/skills/qdpx/qdpx_import.py --qdpx "Thesis-updated.qdpx" --out qdpx-coding-verify`

### Step 7 — Final verification (mandatory)

Only finish when export, validate, and diff complete without integrity errors.

---

## What initial coding is NOT

- Do not interpret, theorise, or explain at this stage — just name what you see.
- Do not merge or rename existing codes — that is focused coding (see
  `cgt-focused-coding` skill).
- Do not leave large stretches of transcript uncoded — if a passage seems
  unimportant, code it as "providing context" or similar rather than skipping it.
- Do not create abstract or conceptual codes at this stage — stay close to the data.

---

## Key Paths

| Item | Path |
|---|---|
| QDPX skill | `.cursor/skills/qdpx/SKILL.md` |
| Target documents | `qdpx-coding/documents/[Doc].md` |
| Existing quotations | `qdpx-coding/quotations/[Doc].md` |
| Codebook | `qdpx-coding/codebook.md` |
| Memos | `qdpx-coding/memos.md` |
