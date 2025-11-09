# Pandoc Integration Guide

This document explains how to use Pandoc to generate PDF and Word documents from your thesis markdown files.

## Prerequisites

### Required Software

1. **Pandoc** (version 2.11 or higher)
   - Download from: https://pandoc.org/installing.html
   - Verify installation: `pandoc --version`

2. **LaTeX Distribution** (for PDF generation)
   - Windows: MiKTeX (https://miktex.org/) or TeX Live
   - The first PDF build may take longer as LaTeX downloads required packages

### Optional

- **Microsoft Word** (for customizing the reference.docx template)

## How It Works

This setup is designed for simplicity. All configuration is stored in YAML files, so building your thesis is as simple as:

```powershell
cd thesis
pandoc -d pandoc-pdf.yaml      # Generates PDF
pandoc -d pandoc-docx.yaml     # Generates Word
```

Or even simpler, just run:

```powershell
.\build-thesis.ps1
```

The YAML files contain everything Pandoc needs: input files, output paths, citation settings, and formatting options. No complex command-line arguments needed!

## Project Structure

```
thesis/
├── 0. abstract.md              # Thesis abstract
├── 1. introduction.md           # Introduction chapter
├── 2. Literature review.md      # Literature review chapter
├── 3. Methodology.md            # Methodology chapter
├── 4. Findings.md              # Findings chapter
├── 5. Discussion.md            # Discussion chapter
├── 6. Conclusion.md            # Conclusion chapter
├── references.bib              # BibTeX bibliography
├── metadata.yaml               # Document metadata (title, author, etc.)
├── pandoc-pdf.yaml             # PDF generation settings (includes input/output)
├── pandoc-docx.yaml            # Word generation settings (includes input/output)
└── reference.docx              # Word styling template

build-thesis.ps1                # Main build script
create-reference-docx.ps1       # Helper script to create Word template
```

## Initial Setup

### 1. Install Pandoc and LaTeX

Make sure both Pandoc and a LaTeX distribution are installed on your system.

### 2. Create Reference Document Template

Run the helper script to create a basic Word template:

```powershell
.\create-reference-docx.ps1
```

This creates `thesis/reference.docx`. You can customize it in Word:

1. Open `thesis/reference.docx` in Microsoft Word
2. Modify the styles (Heading 1, Heading 2, Normal, etc.):
   - Font: Times New Roman, 12pt
   - Line spacing: 1.5
   - Margins: 2.5cm
3. Save and close

The styles you set will be applied to all future Word outputs.

### 3. Update Metadata

Edit `thesis/metadata.yaml` to include your information:

```yaml
---
title: "Your Thesis Title"
author: "Your Name"
date: "November 2025"
---
```

## Building Your Thesis

### Simple Build

To generate both PDF and Word documents:

```powershell
.\build-thesis.ps1
```

Output files will be created in the `output/` directory:
- `output/thesis.pdf`
- `output/thesis.docx`

### Build Individual Formats

All configuration (input files, output paths, settings) is stored in the YAML files, making builds very simple:

**PDF only:**
```powershell
cd thesis
pandoc -d pandoc-pdf.yaml
```

**Word only:**
```powershell
cd thesis
pandoc -d pandoc-docx.yaml
```

**Both formats (chained commands):**
```powershell
cd thesis; pandoc -d pandoc-pdf.yaml; pandoc -d pandoc-docx.yaml
```

The YAML files specify everything Pandoc needs:
- Input files (all thesis chapters in order)
- Output file paths
- Metadata file location
- Bibliography and citation settings
- Formatting options

## Writing with Citations

### Citation Syntax

Use `@citationkey` in your markdown files to cite references from `references.bib`:

**Parenthetical citations:**
- Single author: `[@smith2023]` → (Smith, 2023)
- Multiple authors: `[@smith2023; @jones2024]` → (Smith, 2023; Jones, 2024)
- With page number: `[@smith2023, p. 42]` → (Smith, 2023, p. 42)

**Narrative citations:**
- `@smith2023` → Smith (2023)
- `@smith2023 [p. 42]` → Smith (2023, p. 42)

### Adding New References

1. Open `thesis/references.bib`
2. Add new BibTeX entries (use tools like Zotero, Mendeley, or Google Scholar for export)
3. Use the citation key in your markdown files

**Example BibTeX entry:**

```bibtex
@article{author2023,
  author = {Author, First and Author, Second},
  title = {Article Title},
  journal = {Journal Name},
  volume = {10},
  number = {2},
  pages = {123--145},
  year = {2023},
  doi = {10.1234/journal.2023.001},
  url = {https://doi.org/10.1234/journal.2023.001}
}
```

## Tips and Best Practices

### Citations
- Keep citation keys consistent (e.g., `author2023`, `authoretal2024`)
- Always include DOI URLs when available
- Use lowercase for BibTeX entry types (`@article`, not `@ARTICLE`)

### Markdown Files
- Keep each chapter in a separate file for easier editing
- Use proper heading hierarchy (# for chapter, ## for section, ### for subsection)
- Markdown as source of truth - always edit .md files, not generated docs

### Building
- Build frequently to catch formatting issues early
- First PDF build may take several minutes (LaTeX package downloads)
- Check both PDF and Word outputs for formatting consistency

### Word to Google Docs
- Upload `output/thesis.docx` to Google Drive
- Right-click and choose "Open with Google Docs"
- Share the Google Doc for collaboration

## Troubleshooting

### "Pandoc not found"
- Install Pandoc from https://pandoc.org/installing.html
- Ensure Pandoc is in your system PATH
- Restart PowerShell after installation

### "pdflatex not found"
- Install a LaTeX distribution (MiKTeX or TeX Live)
- Ensure LaTeX is in your system PATH
- Restart PowerShell after installation

### Missing fonts in PDF
- The PDF configuration uses Times New Roman (standard on Windows)
- If fonts are missing, install them or change `mainfont` in `pandoc-pdf.yaml`

### Citations not appearing
- Check that citation keys match entries in `references.bib`
- Ensure `references.bib` is valid BibTeX format
- Verify that `citeproc: true` is set in the YAML configs

### Word template not applying
- Make sure `reference.docx` exists in the `thesis/` directory
- Run `.\create-reference-docx.ps1` to regenerate if needed
- Customize styles in Word and save

## Customization

### Changing Citation Style

To use a different citation style (e.g., Chicago, MLA):

1. Download a CSL file from https://github.com/citation-style-language/styles
2. Save it in the `thesis/` directory
3. Update both `pandoc-pdf.yaml` and `pandoc-docx.yaml`:
   ```yaml
   csl: thesis/chicago-author-date.csl
   ```

### Adjusting PDF Layout

Edit `thesis/pandoc-pdf.yaml` to change:
- Margins: `geometry` section
- Line spacing: `linestretch`
- Fonts: `mainfont`, `sansfont`, `monofont`
- Page size: `classoption`

### Adjusting Word Layout

Edit styles in `thesis/reference.docx` using Microsoft Word.

## Additional Resources

- Pandoc Manual: https://pandoc.org/MANUAL.html
- Pandoc Citations: https://pandoc.org/MANUAL.html#citations
- BibTeX Guide: https://www.bibtex.org/
- CSL Styles: https://citationstyles.org/
- LaTeX Help: https://www.latex-project.org/help/

## Support

For issues specific to:
- **Pandoc**: https://github.com/jgm/pandoc/issues
- **LaTeX**: https://tex.stackexchange.com/
- **Citations**: Check your .bib file syntax with an online validator

