---
name: thesis-writing
description: >
  Write, edit, and develop thesis chapters using coded QDPX workspace data, APA 7
  citations, and Charmaz's grounded theory framework. Use when the user wants
  to work on any thesis chapter (Introduction, Literature Review, Methodology,
  Findings, Discussion, Conclusion), draw coded data into written narrative,
  write up findings from coded QDPX data, structure arguments, or draft academic
  prose for the thesis.
---

# Thesis Writing

## Chapter files

All chapters live in `thesis/`:

| File | Chapter |
|---|---|
| `thesis/0. abstract.md` | Abstract |
| `thesis/1. Introduction.md` | Introduction |
| `thesis/2. Literature review.md` | Literature Review |
| `thesis/3. Methodology.md` | Methodology |
| `thesis/4. Findings.md` | Findings |
| `thesis/5. Discussion.md` | Discussion |
| `thesis/6. Conclusion.md` | Conclusion |
| `thesis/references.bib` | BibTeX bibliography |

---

## Before writing: load context

Always load the relevant context before drafting or editing:

**For Findings or Discussion:**
1. Run the QDPX import to get a fresh snapshot:
   ```powershell
   python .cursor/skills/qdpx/qdpx_import.py --qdpx "Thesis.qdpx" --out qdpx-coding
   ```
2. Read `qdpx-coding/codebook.md` — codes, categories, and descriptions
3. Read `qdpx-coding/memos.md` — the analytical thinking and theoretical hypotheses
4. Read the relevant `qdpx-coding/quotations/[Doc].md` files — actual participant quotes to use as evidence

**For Literature Review or Introduction:**
- Use the `consensus-apa7-citations` skill to search for papers and add them with correct citations.

**For all chapters:**
- Apply APA 7 citation formatting. See [apa7-references/SKILL.md](../apa7-references/SKILL.md) for the full reference.

---

## Writing the Findings chapter

The Findings chapter presents what participants *did* — grounded in the coded data. It does not interpret or explain (that is the Discussion).

**Structure per finding:**
1. State the finding as a category or focused code in a subheading (gerund phrase where possible).
2. Develop the pattern in 2–3 sentences using codes as analytical vocabulary.
3. Anchor each claim in at least one direct participant quote:
   - Use `qdpx-coding/quotations/` to find the strongest quotes.
   - Format as a block quote with attribution: `— *[Participant Name]*`
4. Show variation: where participants differ on this theme, name it explicitly.

**Draw quotes from QDPX import — not from memory.** Copy verbatim text from `qdpx-coding/quotations/[Doc].md`.

**Anonymisation:** Check with the researcher whether participants should be named or anonymised before including names.

---

## Writing the Discussion chapter

The Discussion interprets the findings against the literature and builds toward theory. It answers: *what does this mean, and what does it contribute?*

**Structure:**
1. Restate the key finding briefly (one sentence — do not reproduce the full Findings text).
2. Connect to the literature: what does this confirm, extend, or contradict?
   - Use `consensus-apa7-citations` if a relevant paper needs to be found.
   - Use existing BibTeX entries from `thesis/references.bib`.
3. Elevate to theory: what does Charmaz's framework say about this category? What does it suggest about the phenomenon under study?
4. Note limitations or alternative interpretations honestly.

---

## Writing the Literature Review

- Each section should end with a clear statement of what is *not yet known* — the gap this thesis addresses.
- Use `consensus-apa7-citations` to find and integrate academic sources.
- All citations must be APA 7. See [apa7-references/SKILL.md](../apa7-references/SKILL.md).

---

## Citations and references

- **In-text format:** `(Author, Year)` or narrative `Author (Year)`.
- **All references** go in `thesis/references.bib` as BibTeX entries.
- For full APA 7 rules and format examples, read [apa7-references/SKILL.md](../apa7-references/SKILL.md).
- For searching new papers, use the `consensus-apa7-citations` skill.

---

## Academic writing style

- Write in third person or passive voice (standard for thesis work in this field).
- Use gerund-phrase code names as analytical vocabulary: *"legitimising AI investment"*, not *"when participants talked about budget"*.
- One claim per paragraph. Lead with the claim, then support with evidence.
- Avoid hedging with "I think" or "it seems" — state findings directly and qualify with evidence.
- Keep participant voice distinct from analytical voice: quotes are indented block quotes, analysis is plain prose.

---

## Key skill references

| Task | Skill |
|---|---|
| Draw coded data from QDPX | `.cursor/skills/qdpx/SKILL.md` |
| Format APA 7 citations | `.cursor/skills/apa7-references/SKILL.md` |
| Search and add literature | `.cursor/skills/consensus-apa7-citations/SKILL.md` |
| Check memos for analytical direction | `qdpx-coding/memos.md` |
