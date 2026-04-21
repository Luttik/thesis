---
name: apa7-references
description: Format academic references and in-text citations in APA 7th edition style in thesis Markdown files. Use when formatting a reference list, checking citation style, writing in-text citations, or when the user asks about APA 7 format, DOI formatting, or reference list entries.
---

# APA 7 Reference Formatting

## In-Text Citations

| Situation | Format |
|---|---|
| Single author | (Smith, 2023) |
| 2 authors | (Smith & Jones, 2023) |
| 3+ authors | (Smith et al., 2023) |
| Direct quote | (Smith, 2023, p. 15) or (pp. 15–16) |
| No author | ("Article Title," 2023) |
| Narrative | Smith (2023) argues that… |

## Reference List Formats

### Journal article
```
Author, A. A., & Author, B. B. (Year). Title of article. *Journal Name*, Volume(Issue), pages. https://doi.org/10.xxxx/xxxxx
```

### Book
```
Author, A. A. (Year). *Title of book*. Publisher. https://doi.org/10.xxxx/xxxxx
```

### Book chapter
```
Author, A. A. (Year). Title of chapter. In B. B. Editor (Ed.), *Title of book* (pp. xx–xx). Publisher. https://doi.org/10.xxxx/xxxxx
```

### Conference paper
```
Author, A. A. (Year). Title of paper. In *Proceedings of Conference Name* (pp. xx–xx). Publisher. https://doi.org/10.xxxx/xxxxx
```

## DOI Rules

- Always use full URL: `https://doi.org/10.xxxx/...`
- Never use `doi:` prefix or `dx.doi.org`
- If no DOI: use publisher URL, or omit

## Formatting Rules

- Journal and book titles → *italics*
- Article/chapter titles → plain text (no quotes in reference list)
- Author names → `Last, F. M.` (initials, not full first names)
- Issue number → in parentheses after volume: `15(3)`
- Use en-dash for page ranges: `45–67`

## Quality Checklist

- [ ] Every in-text citation has a matching reference list entry
- [ ] Every reference entry has a corresponding in-text citation
- [ ] DOIs formatted as `https://doi.org/...`
- [ ] Journal/book titles italicised
- [ ] Author names use initials
- [ ] Year in parentheses, not brackets
- [ ] No mixed citation styles

## Common Mistakes

1. `doi:` prefix instead of `https://doi.org/`
2. Missing italics on journal/book titles
3. Full first names instead of initials
4. `[Year]` instead of `(Year)`
5. Mixing APA with other styles in the same document
