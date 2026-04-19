---
name: cgt-initial-coding
description: >
  Apply Charmaz's (2006) initial/open coding to a single interview transcript in Atlas.ti.
  Guides line-by-line, gerund-based coding with preference for existing codes and in vivo
  language. Includes a mandatory researcher review before export. Use when the user wants
  to code a new document, do open coding, or start the first pass on a transcript.
---

# CGT Initial Coding Skill

## Purpose

Perform **initial coding** as described in Charmaz (2006, Ch. 2): a close, line-by-line
reading of a transcript that codes actions and processes, staying near the participants'
own language. This skill produces new `<!-- quote -->` annotations in the Atlas.ti
document files and writes a code memo for any genuinely new code introduced.

**Always use this skill in combination with the Atlas.ti skill.** Read
`.cursor/skills/atlasti/SKILL.md` first to understand the import/export mechanics
and file formats before proceeding.

---

## Workflow

### Step 1 — Sync and import (Atlas.ti skill Steps 1–2)

Follow Steps 1 and 2 from the Atlas.ti skill:
1. Push the Atlas.ti git backup.
2. Run the import: `python .cursor/skills/atlasti/atlasti_import.py`

### Step 2 — Read context

Read in this order:
1. `atlas-coding/codebook.md` — internalize the full list of existing codes
2. `atlas-coding/quotations/[Target Doc].md` — see what has already been coded in this document so you do not duplicate
3. `atlas-coding/documents/[Target Doc].md` — the full interview text with `<!-- seg:N -->` markers

### Step 3 — Code segment by segment

Work through every `<!-- seg:N -->` block in the document that does not already have a
quotation covering it. For each meaningful passage:

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
   brief code memo for it (see Step 4). **New codes referenced in `<!-- quote -->`
   annotations are automatically created in Atlas.ti by the export script — no
   manual Atlas.ti step required.**
3. If an existing code is close but not quite right, note this as a candidate for
   renaming in focused coding — do not rename it now.

**Annotate using the Atlas.ti format:**
```markdown
<!-- quote: `Existing Code Name`, `Another Code` -->
Exact verbatim text from the segment below.
<!-- /quote -->
```

Rules (from Atlas.ti skill):
- The quoted text must be **verbatim** — copy character-for-character from below the
  `<!-- seg:N -->` marker.
- Code names must match `codebook.md` headings exactly (capitalisation, punctuation).
- Do not edit or remove `<!-- seg:N -->` markers.

### Step 4 — Write memos as you code (do not wait until the end)

Memo writing is not a separate phase — it interrupts coding whenever something
analytically interesting surfaces. Use the `cgt-memo-writing` skill templates for
all memos and append them to `atlas-coding/memos.md` immediately.

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

1. **New quotations summary** — a list of every `<!-- quote -->` annotation added,
   showing: segment number, codes applied, first 15 words of the quoted text.
2. **New codes introduced** — list of any code names that do not appear in
   `codebook.md` and will be created in Atlas.ti.
3. **Skipped segments** — any segments that were left uncoded and a brief reason
   (e.g. "administrative filler", "already coded in quotations file").

Wait for explicit researcher approval ("yes", "go ahead", or similar) before exporting.
If the researcher says "edit X" or "no", make the requested changes and re-present
the summary.

### Step 6 — Export (Atlas.ti skill Step 5)

After approval:
1. Confirm Atlas.ti is closed.
2. Run dry-run: `python .cursor/skills/atlasti/atlasti_export.py --dry-run`
3. Show the dry-run output to the researcher.
4. Run the actual export: `python .cursor/skills/atlasti/atlasti_export.py`
5. Confirm success and instruct the researcher to reopen Atlas.ti.

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
| Atlas.ti skill | `.cursor/skills/atlasti/SKILL.md` |
| Target documents | `atlas-coding/documents/[Doc].md` |
| Existing quotations | `atlas-coding/quotations/[Doc].md` |
| Codebook | `atlas-coding/codebook.md` |
| Memos | `atlas-coding/memos.md` |
