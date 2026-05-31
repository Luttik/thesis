---
name: findings-quote-artifact
description: >
  Produce a standalone HTML quote-reference artifact for a findings section.
  Lists  quotes per subsection that are not currently used in the
  thesis text, styled with the project's standard quote-card template.
  Use when working on any section of the Findings chapter and you want to
  see which quotes are available for a given set of subsections or codes,
  or when the user asks to "create a quote artifact", "show available quotes",
  "what quotes do we have for X section", or "update the quotes artifact".
---

# findings-quote-artifact

Produces a standalone HTML file in `artifacts/` listing QDPX-coded quotes (or quotes taken directly from the transcripts) that are not yet used in the thesis text. The artifact is read-only reference. All docx edits use the tracked-changes workflow. The HTML chrome is fixed; only content changes between uses.

**Template:** [`templates/quote-artifact.html`](templates/quote-artifact.html) — copy verbatim, fill in content.

---

## Interviewee reference

| # | Name | Role |
|---|---|---|
| 1 | Andreea Bulisache | External AI advisor |
| 2 | Arjan Dijk | Marketing manager |
| 3 | Berfun Goodwin | External AI advisor + marketing |
| 4 | Dennis Goedegebuure | External AI advisor |
| 5 | Erik Hilhorst | Internal AI expert |
| 6 | Erica Hahn | Marketing manager |
| 7 | Georgio Mosis | External AI advisor |
| 8 | Jon Stephan | Internal AI expert |
| 9 | Lauren Stokowski | Internal AI expert (agency) |
| 10 | Maarten Mantjes | External AI advisor |
| 11 | Rolf Mulder | External AI advisor |
| 12 | Scott Brinker | External AI advisor |
| 13 | Tim Wiegel | External AI advisor |
| 14 | Floris Reguoin | External AI advisor |
| 15 | Sylvia Vroklage | External AI advisor |
| 16 | Anonymous | Internal AI expert |
| 17 | Karin Boon | External AI advisor |

---

## Workflow

**1. Identify target section(s)** from the user's request and map to QDPX codes via the codebook.

**2. Find quotes already in the live text**
```powershell
pandoc "Thesis Draft - Daan Luttik - MBA.docx" -t markdown --track-changes=accept -o ".cache/thesis-current.md"
```
Scan the target section for `Interviewee N` attributions — these go in the `.note` box.

**3. Pull quotes from the QDPX**
Load `.cache/qdpx_quotes_by_code.json`. If absent or stale (older than the current `.qdpx`), regenerate using the QDPX extraction script. Select codes matching the target section's analytical cluster.

**4. Filter** — exclude quotes whose text already appears (verbatim or near-verbatim) in the live section.

**5. Write the artifact**
- Filename: `artifacts/<section-slug>-quotes.html` (e.g. `observing-section-quotes.html`, `steering-section-quotes.html`)
- Copy `templates/quote-artifact.html` verbatim; fill in title, sections, code groups, and cards
- One `.section` div per subsection; one `.code-group` per QDPX code; max 5 `.quote-card`s per code

**6. Report** — output filename + quote count per subsection + any interviewees newly represented.

---

## Conventions

| Rule | Detail |
|---|---|
| Badge class | Matches section prefix: `b41` `b42` `b43` `b44` `b45` |
| Attribution | Always `<span class="num">N</span> Name · role` — number is mandatory |
| `.note` box | Required on every subsection; lists interviewee numbers already in live text |
| Quote length | Truncate at ~300 chars with `…`; use full text only if it is the sole quote for a code |
| Quotes per code | Max 5; choose most analytically distinct if more exist |
| Exclusion rule | Never include quotes already block-quoted in the live section |
| Updating | Overwrite the existing file; never create a second copy |
