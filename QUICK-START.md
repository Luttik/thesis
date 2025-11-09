# Quick Start Guide - Pandoc Thesis Integration

## What Was Set Up

Your thesis project now uses Pandoc to convert markdown files into professional PDF and Word documents with proper APA 7th citations.

## Files Created

### Core Files
- `thesis/references.bib` - Bibliography in BibTeX format
- `thesis/metadata.yaml` - Document title, author, and metadata
- `thesis/pandoc-pdf.yaml` - PDF generation settings (LaTeX, APA style)
- `thesis/pandoc-docx.yaml` - Word generation settings

### Build Scripts
- `build-thesis.ps1` - Main script to generate PDF and Word outputs
- `create-reference-docx.ps1` - Helper to create Word template

### Documentation
- `thesis/PANDOC-README.md` - Comprehensive guide
- `.gitignore` - Excludes output files from Git

### Modified Files
- `thesis/1. introduction.md` - Updated citations to use `@citationkey` syntax

## Getting Started (3 Steps)

### 1. Install Prerequisites

**Install Pandoc:**
- Download: https://pandoc.org/installing.html
- Verify: `pandoc --version`

**Install LaTeX (for PDF):**
- Windows: https://miktex.org/download
- Verify: `pdflatex --version`

### 2. Create Word Template

```powershell
.\create-reference-docx.ps1
```

This creates `thesis/reference.docx`. Optionally customize it in Word for your preferred styling.

### 3. Build Your Thesis

```powershell
.\build-thesis.ps1
```

Your thesis will be generated in the `output/` directory:
- `output/thesis.pdf` - PDF version
- `output/thesis.docx` - Word version (upload to Google Docs if needed)

### Build Individual Formats (Optional)

All settings are in the YAML files, so you can run Pandoc directly:

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

**Both formats (one command):**
```powershell
cd thesis; pandoc -d pandoc-pdf.yaml; pandoc -d pandoc-docx.yaml
```

## Next Steps

### Update Metadata
Edit `thesis/metadata.yaml` with your actual information:

```yaml
title: "Your Thesis Title"
author: "Daniël Timotheüs Luttik"
date: "November 2025"
```

### Add More Citations

1. Add entries to `thesis/references.bib` (use Google Scholar's BibTeX export)
2. Cite in markdown using `[@citationkey]` or `@citationkey`
3. Rebuild with `.\build-thesis.ps1`

### Complete Your Chapters

The following files are currently empty/placeholder:
- `thesis/2. Literature review.md`
- `thesis/3. Methodology.md`
- `thesis/4. Findings.md`
- `thesis/5. Discussion.md`
- `thesis/6. Conclusion.md`

As you write them, the build script will automatically include them in the output.

## Citation Examples

In your markdown files:

```markdown
Recent research shows significant impact [@mayer2025].

According to @holmstrom2022, AI represents a new wave of transformation.

Multiple studies support this [@teece1997; @vidal2022].

As stated: "quote here" [@brinker2025, p. 35].
```

## Workflow

1. **Write** in markdown files (your single source of truth)
2. **Build** with `.\build-thesis.ps1` whenever you want to see formatted output
3. **Share** the Word document or PDF with supervisors/reviewers
4. **Edit** the markdown files based on feedback (never edit the generated docs directly)

## Troubleshooting

**"Pandoc not found"** → Install Pandoc and restart PowerShell

**"pdflatex not found"** → Install LaTeX distribution (MiKTeX)

**Citations not working** → Check citation keys match `references.bib` entries

**Need help?** → Read `thesis/PANDOC-README.md` for detailed documentation

## Tips

- Build frequently to catch formatting issues early
- First PDF build may take 5-10 minutes (LaTeX downloads packages)
- Keep markdown files as your source of truth
- Upload Word file to Google Drive for online collaboration
- PDF is best for final submission

---

**Your thesis project is now ready! Run `.\build-thesis.ps1` to test it out.**

