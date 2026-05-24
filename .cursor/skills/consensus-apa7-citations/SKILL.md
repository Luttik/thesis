---
name: consensus-apa7-citations
description: Search papers with the Consensus MCP and integrate findings into thesis markdown with APA 7 in-text citations plus BibTeX entries in thesis/references.bib. Use when the user asks to expand literature sections, add academic sources, or format APA citations/references.
---

# Consensus APA7 Citations

## Purpose

Use this skill to turn Consensus MCP search results into:
1. thesis-ready evidence text with APA 7 in-text citations, and
2. matching BibTeX entries in `thesis/references.bib`.

## Default Targets

- Literature file: `thesis/2. Literature review.md` (or user-specified chapter)
- Bibliography file: `thesis/references.bib`

## Workflow

1. Detect intent:
   - If the question is about recent developments in AI, run search with `year_min = 2023`.
   - Otherwise, pick a year filter based on user scope.
2. Run `project-0-thesis-consensus.search` with a focused academic query.
2. Select high-quality papers (prefer peer-reviewed journals, stronger citation counts, and topical fit).
3. Write or revise the section text and add APA 7 in-text citations:
   - Narrative: `Author (Year) ...`
   - Parenthetical: `(Author, Year)`
   - 2 authors: `(Author & Author, Year)`
   - 3+ authors: `(Author et al., Year)`
4. Create/update BibTeX entries in `thesis/references.bib` using stable citekeys.
5. Ensure each in-text citation has a matching BibTeX key and vice versa.
6. If metadata is incomplete, add `note = {Metadata incomplete; verify publisher page}`.

## Query Filtering Rules

- The Consensus MCP `search` tool supports:
  - `year_min`, `year_max`, `human`, `sample_size_min`, `sjr_max`
- It does **not** expose a `citation_min` argument.
- Therefore, enforce citation quality as a post-processing step:
  1. Run search (with `year_min = 2023` for recent AI topics).
  2. Filter returned papers to `citation_count >= 50`.
  3. If fewer than 3 papers remain, relax threshold to `>= 20` and explicitly say that fallback was used.
  4. If still sparse, keep threshold open but prioritize highest-cited items and Q1/Q2 journals when possible.

## APA 7 Formatting Reference

For full formatting rules, reference table examples, and the quality checklist, read [apa7-references/SKILL.md](../apa7-references/SKILL.md).

## BibTeX Rules (APA7-aligned)

- Use `@article` for journal papers, `@inproceedings` for conference papers, `@book` for books.
- Include fields when available:
  - `author`, `title`, `year`
  - `journal` (or `booktitle` for conferences)
  - `volume`, `number`, `pages`
  - `doi`, `url`
- DOI format must be canonical:
  - `doi = {10.xxxx/...}`
  - `url = {https://doi.org/10.xxxx/...}`
- Keep author names as `Last, First and Last, First`.
- Avoid duplicate keys by checking `references.bib` first.

## Citekey Convention

Use `lastnameYYYYshorttitle`, for example:
- `Hoyer2024generative`
- `Mariani2024innovation`
- `Aladwani2022virtual`

If collision occurs, append `a`, `b`, etc.

## Output Contract

When using this skill, always deliver:
1. Updated thesis text with APA 7 in-text citations.
2. Added/updated BibTeX entries in `thesis/references.bib`.
3. A short validation note confirming:
   - no duplicate BibTeX keys introduced,
   - DOI URL formatting is correct,
   - all inserted in-text citations map to bibliography entries.

## Consensus MCP Presentation Requirement

When presenting Consensus search results to the user:
- List each paper individually as `[Paper Title](url)`.
- Include year, journal, and citation count for each item.
- At the end of the response, include the exact Consensus usage/sign-up message from the tool output word-for-word.
