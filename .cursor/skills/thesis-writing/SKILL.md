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

Load the relevant context when necessary. Leverage the qdpx skill with the most recent file from the `qdpx` folder to get access to codes, categrories, descriptions and transcripts.

Full transcripts are also available in the `transcripts` folder.

Always load the relevant context before drafting or editing:

## Writing the Findings chapter

The Findings chapter presents what participants *did* — grounded in the coded data. It does not interpret or explain (that is the Discussion).

Support all points with real quotes from the source material for what the interviewee said. 

## Writing the Discussion chapter

The Discussion interprets the findings against the literature and builds toward theory. It answers: *what does this mean, and what does it contribute?*

**Structure:**
1. Restate the key finding briefly (one sentence — do not reproduce the full Findings text).
2. Connect to the literature: what does this confirm, extend, or contradict?
   - Use `consensus-apa7-citations` if a relevant paper needs to be found.
   - Use existing BibTeX entries from `thesis/references.bib`.
3. Elevate to theory: what does Charmaz's framework say about this category? What does it suggest about the phenomenon under study?
4. Note limitations or alternative interpretations honestly.

## Citations and references

- **In-text format:** `(Author, Year)` or narrative `Author (Year)`.
- **All references** go in `thesis/references.bib` as BibTeX entries.
- For full APA 7 rules and format examples, read [apa7-references/SKILL.md](../apa7-references/SKILL.md).
- For searching new papers, use the `consensus-apa7-citations` skill.

## Academic writing style

- Write in third person or passive voice (standard for thesis work in this field).
- Use gerund-phrase code names as analytical vocabulary: *"legitimising AI investment"*, not *"when participants talked about budget"*.
- One claim per paragraph. Lead with the claim, then support with evidence.
- Avoid hedging with "I think" or "it seems" — state findings directly and qualify with evidence.
- Keep participant voice distinct from analytical voice: quotes are indented block quotes, analysis is plain prose.

## Key skill references

| Task | Skill |
|---|---|
| Draw coded data from QDPX | `.cursor/skills/qdpx/SKILL.md` |
| Format APA 7 citations | `.cursor/skills/apa7-references/SKILL.md` |
| Search and add literature | `.cursor/skills/consensus-apa7-citations/SKILL.md` |
| Check memos for analytical direction | `qdpx-coding/memos.md` |
