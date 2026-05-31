---
name: findings-quote-artifact
description: >
  Produce a standalone HTML quote-reference artifact for a findings section.
  Lists quotes per subsection that are not currently used in the
  thesis text, styled with the project's standard quote-card template.
  Use when working on any section of the Findings chapter and you want to
  see which quotes are available for a given set of subsections or codes,
  or when the user asks to "create a quote artifact", "show available quotes",
  "what quotes do we have for X section", or "update the quotes artifact".
---

# findings-quote-artifact

Produces a standalone HTML file in `artifacts/` listing QDPX-coded quotes (or quotes taken directly from transcripts) that are not yet used in the thesis text. The artifact is read-only reference. All docx edits use the tracked-changes workflow.

**Canonical style:** [`artifacts/steering-section-quotes.html`](../../../artifacts/steering-section-quotes.html) — match this layout exactly.

**Template:** [`templates/quote-artifact.html`](templates/quote-artifact.html) — copy verbatim (CSS included); fill in content only.

---

## HTML structure (required)

Use this hierarchy — do not substitute flat `h2`/`h3`/`card` layouts:

```
.wrap
  header
    h1          — "§4.X.X [Section] — additional QDPX quotes"
    p           — standard subtitle (see template)
  .section      — one per thesis subsection
    .section-header
      .badge.b4X   — coloured § badge (b41–b45)
      h2            — subsection heading from thesis
    .note           — interviewees already cited in live text
    .code-group     — one per QDPX code
      .code-label   — "[Code name] — N quotes total in corpus"
      .quote-card   — max 5 per code
        .interviewee
          span.num  — interviewee number
          Name · role
        blockquote  — quote text (no surrounding quotation marks)
```

---

## Styling rules

| Element | Rule |
|---|---|
| CSS | Copy from `templates/quote-artifact.html` unchanged — do not add custom colours, legends, or badge rows |
| Badge class | `b41` (blue), `b42` (green), `b43` (purple), `b44` (orange), `b45` (cyan) — matches section prefix |
| Attribution | Always above the quote: `<span class="num">N</span> Name · role` |
| Quote body | `<blockquote>` only — serif font, left border, no green highlight box |
| `.note` box | Yellow callout on every subsection; lists interviewee numbers already in live text |
| Width | `max-width: 900px` via `.wrap` — not 1080px |

### Do not include (observing-style anti-patterns)

These appeared in an older artifact and must **not** be used:

- `.page`, `.card`, `.quote`, `.meta`, `.legend`, `.section-stat`, `.code-badge`, `.int-badge`, `.doc-badge`
- Quote-first layout with metadata badges below the quote
- "Currently used" / yellow-left-border cards for quotes already in the draft
- Colour legend for AI vs user-written text
- Footer with QDPX source metadata
- Serif page title (`h1` at 32px) — use the template's sans-serif `header h1` at 24px bold
- Inline `"quoted text"` inside a div — use `<blockquote>` without extra quote marks

Uncoded transcript quotes may still be included, but use the same `.quote-card` / `.interviewee` / `blockquote` pattern. Note them in `.code-label` (e.g. `uncoded — theme name`) rather than inventing new badge styles.

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
Scan the target section for `Interviewee N` attributions — these go in each subsection's `.note` box.

**3. Pull quotes from the QDPX**
Load `.cache/qdpx_quotes_by_code.json`. If absent or stale (older than the current `.qdpx`), regenerate using the QDPX extraction script. Select codes matching the target section's analytical cluster.

**4. Filter** — exclude quotes whose text already appears (verbatim or near-verbatim) in the live section. Do not render excluded quotes as separate "already used" cards; mention them only in `.note`.

**5. Write the artifact**
- Filename: `artifacts/<section-slug>-quotes.html` (e.g. `steering-section-quotes.html`)
- Copy `templates/quote-artifact.html` verbatim; replace placeholders only
- One `.section` per subsection; one `.code-group` per QDPX code; max 5 `.quote-card`s per code
- Optional analytical sub-headings go in `.code-label` text, not as `h3` elements

**6. Report** — output filename + quote count per subsection + any interviewees newly represented.

---

## Content conventions

| Rule | Detail |
|---|---|
| Quote length | Truncate at ~300 chars with `…`; use full text only if it is the sole quote for a code |
| Quotes per code | Max 5; choose most analytically distinct if more exist |
| Exclusion rule | Never include quotes already block-quoted in the live section |
| Code label | Format: `[Code name] — N quotes total in corpus` |
| Updating | Overwrite the existing file; never create a second copy |
| Analytical notes | Brief context (e.g. uncoded themes, terminology mismatches) goes in `.note` at subsection level — not in a page-wide intro block |
