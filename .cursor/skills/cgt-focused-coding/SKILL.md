---
name: cgt-focused-coding
description: >
  Apply Charmaz's (2006) focused coding to synthesize and elevate initial codes into
  categories. Reviews the full codebook to merge redundant codes, rename noun-phrase
  codes to gerunds, write code descriptions, and identify analytically central categories.
  Includes a mandatory researcher review before any changes are exported. Use when the
  user wants to synthesize codes, build categories, clean the codebook, or move from
  initial to focused codes.
---

# CGT Focused Coding Skill

## Purpose

Perform **focused coding** as described in Charmaz (2006, Ch. 2): a selective,
comparative pass across all initial codes to identify those that are most frequent,
most analytically rich, or most theoretically promising. This skill works at the
codebook level — refining names, writing definitions, proposing merges, and flagging
candidate categories — without creating new quotations.

**Always use this skill in combination with the QDPX skill.** Read
`.cursor/skills/qdpx/SKILL.md` first to understand the import/export mechanics
and file formats before proceeding.

---

## Workflow

### Step 1 — Import QDPX workspace snapshot

Run the import:
1. `python .cursor/skills/qdpx/qdpx_import.py --qdpx "Thesis.qdpx" --out qdpx-coding`

### Step 2 — Read the full codebook and quotations

1. Read `qdpx-coding/codebook.md` in full — note usage counts, hierarchy, and any
   existing descriptions.
2. Read all files in `qdpx-coding/quotations/` — see which codes cluster together
   on the same quotations (co-occurrence is a signal of conceptual overlap or
   a potential relationship).
3. Read `qdpx-coding/memos.md` — the researcher's existing analytical thinking
   should inform which codes are worth elevating.

### Step 3 — Analyse and propose changes

Work through the codebook systematically. For each code consider:

**CGT focused coding principles (Charmaz 2006):**
- **Frequency is a starting signal, not the only criterion.** A code used once but
  capturing something theoretically distinctive is more important than a code used
  ten times that just restates the obvious.
- **Ask: what does this code DO analytically?** Does it name a process, a tension,
  a strategy, a consequence? If it just names a topic ("AI adoption") it is probably
  still an initial code and needs gerund reformulation.
- **Focused codes become category candidates.** A focused code can subsume several
  initial codes. For example, initial codes "fighting for budget", "justifying ROI
  upward", and "seeking executive sponsorship" might all fall under the focused code
  "legitimising AI investment".
- **Constant comparison.** Compare each code with every other code: are they the same
  action? A subspecies of the same action? A contrasting action?

Produce a proposed change list covering:

#### A. Merges
Codes that capture the same action and should be collapsed into one canonical code.

Format:
```
MERGE: `Code A`, `Code B`, `Code C` → `Canonical Focused Code` (reason)
```

The canonical name should be a gerund phrase. All quotations currently assigned to
the merged codes will be reassigned to the canonical code.

In `codebook.md`: delete the entries for the codes being absorbed; rename the
surviving entry to the canonical name.

#### B. Renames
Codes that are conceptually sound but named as noun phrases rather than gerunds.

Format:
```
RENAME: `Old Name` → `New Gerund Name` (reason)
```

In `codebook.md`: change the `### Code Name` heading. The `<!-- id -->` anchor must
not change.

#### C. Descriptions
All codes that remain after merges and renames should have a `**Description**:`
filled in. Write one to two sentences that:
- Define what the code captures (the action, not the topic)
- State what it explicitly excludes (boundary with the most similar code)

#### D. Hierarchy assignments
Propose which parent code path each focused code belongs to (QDPX hierarchy).
If a needed parent path does not yet exist, flag it clearly:

```
NEW PARENT PATH NEEDED: `Legitimising AI: [Child Code]`
```

#### E. Candidate categories
Flag the three to five codes that are most analytically generative — those that
appear across multiple documents, link to multiple other codes, and point toward
a theoretical claim. Mark them:

```
CATEGORY CANDIDATE: `Focused Code Name` — reason (covers N initial codes, appears in X docs)
```

### Step 4 — Review before export (mandatory)

Present the full proposed change list to the researcher in this structure:

```
## Proposed Focused Coding Changes

### Merges (N)
- MERGE: `A`, `B` → `C` — [reason]
...

### Renames (N)
- RENAME: `Old` → `New` — [reason]
...

### New descriptions (N codes)
- `Code Name`: [description text]
...

### Hierarchy assignments (N)
- `Code Name` → parent path `Parent Code: Child Code`
...

### New parent paths needed (before export)
- `Parent Code: Child Code`
...

### Category candidates
- `Code Name` — [reason]
...
```

Wait for explicit researcher approval before making any edits to `codebook.md`.
The researcher may:
- Approve all changes: "yes, go ahead"
- Accept some and reject others: edit the list together conversationally
- Ask for a rationale on a specific merge or rename before deciding

Only proceed to Step 5 after explicit approval of the final change list.

### Step 5 — Apply changes to codebook.md

Make only the approved changes:
- Merges: remove absorbed code entries, rename surviving entry, verify parent path still fits
- Renames: update `### Code Name` heading only (never touch `<!-- id -->`)
- Descriptions: fill in `**Description**:` field
- Parent-path assignments: reflect hierarchy in code headings (for example `Parent: Child`)

Do not change `<!-- id -->` anchors, `**Used in**:` counts, or `**Example**:`
fields — these are read-only fields managed by the import script.

### Step 5b — Write memos as you analyse (do not wait until the end)

Memo writing runs alongside the focused coding analysis, not after it. Use the
`cgt-memo-writing` skill templates and append directly to `qdpx-coding/memos.md`.

**Write a theoretical memo when:**
- A proposed merge reveals that two codes are actually in tension rather than
  synonymous — the tension is the finding, not a reason to abandon the merge
- A candidate category starts to feel like it could explain something beyond the
  data in front of you — follow the theoretical lead immediately
- Comparing codes across documents surfaces a variation in how participants
  perform the same action — note what the variation might mean

**Write an operational memo when:**
- You decide NOT to merge two codes that look similar — document why the
  distinction matters
- A code resists gerund reformulation — this often signals that it is still a
  topic label, not an action; explore what action it is actually pointing at

Do not defer memos to after the full codebook review. If an insight surfaces while
working through the first ten codes, write the memo then and return to the review.

### Step 6 — Write a focused-coding session memo

Append a memo to `qdpx-coding/memos.md` documenting the focused coding session:

```markdown
## Focused Coding Session: [Date]

**Type**: Operational memo  
**Date**: YYYY-MM-DD

**Summary of changes**: N merges, N renames, N descriptions added.  
**Rationale**: [2–3 sentences on the analytical logic driving the merges]  
**Emerging categories**: List the category candidates and a one-sentence hypothesis
for each.  
**Open questions**: What tensions or uncertainties remain in the codebook? What
would theoretical sampling need to resolve?
```

### Step 7 — Export, validate, and diff (QDPX workflow)

After all edits are made:
1. Run export: `python .cursor/skills/qdpx/qdpx_export.py --base "Thesis.qdpx" --in qdpx-coding --out "Thesis-updated.qdpx"`
2. Validate no-loss: `python .cursor/skills/qdpx/qdpx_validate.py --baseline "Thesis.qdpx" --qdpx "Thesis-updated.qdpx"`
3. Review deltas: `python .cursor/skills/qdpx/qdpx_diff.py --old "Thesis.qdpx" --new "Thesis-updated.qdpx"`
4. Re-import for spot check: `python .cursor/skills/qdpx/qdpx_import.py --qdpx "Thesis-updated.qdpx" --out qdpx-coding-verify`

---

## What focused coding is NOT

- Do not create new quotations here — that is initial coding.
- Do not build a full theory — that comes in theoretical coding and memo sorting.
- Do not rename a code just to make it sound more academic — if the initial code
  name is already a good gerund close to the data, keep it.
- Do not merge codes just because they co-occur. Co-occurrence may mean they capture
  different facets of the same situation, which is analytically valuable to preserve.

---

## Key Paths

| Item | Path |
|---|---|
| QDPX skill | `.cursor/skills/qdpx/SKILL.md` |
| Codebook | `qdpx-coding/codebook.md` |
| All quotations | `qdpx-coding/quotations/` |
| Memos | `qdpx-coding/memos.md` |
