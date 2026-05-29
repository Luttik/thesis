---
name: clean-convert-transcript
description: Clean and convert thesis interview transcripts. Applies correction-only ASR cleaning, quote-block formatting for [Me] sections, and pandoc DOCX export. Use when the user asks to "clean transcript X", "convert transcript Y to a docx", "process a transcript", or mentions cleaning/exporting a specific interview file.
---

# Clean & Convert Transcript

Transcripts live in `transcripts/individuals/` as `.md` files (e.g. `transcripts/individuals/Thesis interview Lauren Stokowski.md`). The combined export is built into `output/` via `scripts/build_combined_transcripts.py`.

## Workflow decision

- **"Clean transcript X"** → Step 0 (if needed) + Step 1 (clean) + Step 2 (quote blocks) + offer Step 3
- **"Convert transcript Y to docx"** → Step 2 (quote blocks) + Step 3 (export)
- **"Clean and convert"** → All three steps in order

After every cleaning task, also do the post-cleaning administration step below.

Check the first few lines of the file. If speaker labels are named (e.g. `[Speaker 0]`, `[Daan]`) rather than `[Me]` / `[Them]`, run **Step 0** first.

---

## Step 0 — Normalize speaker labels (if needed)

Use when the transcript contains named/numbered labels instead of `[Me]` / `[Them]`.

**Discover labels first:**
```powershell
cd c:\workspace\thesis
python .cursor/skills/clean-convert-transcript/normalize_speakers.py "transcripts\<filename>.md" --list-speakers
```

**Determine who is who** from the filename (the interviewee's name) and the document content (who introduces the study, who answers questions). The interviewer is Daan Luttik → maps to `[Me]`.

**Remap and overwrite:**
```powershell
python .cursor/skills/clean-convert-transcript/normalize_speakers.py "transcripts\<filename>.md" --me "Speaker 1" --them "Speaker 0"
```

Multiple `--them` labels are supported for group interviews. Use `--dry-run` to preview before saving.

---

## Step 1 — Apply correction-only cleaning

### Do
- **Fix clear ASR errors** — wrong word that is obviously a mishear.
- **Fix obvious stutter repetitions** in the same word only: `I I` → `I`, `the the` → `the`, `we we we` → `we`. Do not collapse different words or change meaning.
- **Fix "agentic" misspellings** — ASR often renders it as "agency", "hygenic", "agendic", etc. Use context to confirm.
- **Improve excessive fillers** — leave some to show unclarity, but clean up when multiple fillers and restarts make a sentence almost unreadable.
- **Remove `Me:` filler-only lines** — remove lines containing only acknowledgment words (Yeah, Yep, Mhmm, Okay, Check, Sure, Cool, Interesting, Ja, Oké, Sí, Ya, Yes, No, Nee, Ajá, Indeed, Exactly, Great, Zeker, Duidelijk — and repeated combinations). Keep lines where the filler is followed by substantive content.
- **Merge adjacent `Them:` lines after filler removal** — when removing a `Me:` filler line leaves two adjacent `Them:` turns, merge them into one (the split was caused by the removed interjection).
- **Fix punctuation** that breaks readability (e.g. missing period at end of a turn). Do not add interpretation.

### Do not
- **Do not remove fillers *within* substantive lines** — speech patterns are data.
- **Do not remove `Them:` filler lines** — interviewee speech is data.
- **Do not rewrite or "improve"** participants' wording.
- **Do not change meaning** or add interpretation.
- **Do not merge or split** substantive content across turns (only merge `Them:` turns split by a removed interjection).
- **Do not normalize language** (e.g. translate Dutch → English) unless explicitly asked.

After editing, show the user a brief diff summary (lines changed, lines removed) and ask for confirmation before saving.

---

## Step 2 — Format [Me] block quotes

Run `quote_me_sections.py` to wrap all `[Me]` sections in markdown block quotes (relevant when transcripts use `[Me]` / `[Them]` section headers rather than the `Me:` / `Them:` inline prefix format):

```powershell
cd c:\workspace\thesis
python .cursor/skills/clean-convert-transcript/quote_me_sections.py "transcripts\<filename>.md"
```

If the transcript uses `Me:` / `Them:` inline labels (not `[Me]` section blocks), skip this step.

---

## Step 3 — Export to DOCX

Convert the cleaned markdown file to DOCX using pandoc:

```powershell
$md = "c:\workspace\thesis\transcripts\<filename>.md"
$docx = [System.IO.Path]::ChangeExtension($md, "docx")
pandoc $md -o $docx
Write-Host "Exported: $docx"
```

To convert **all** transcripts at once, run from the project root. The script applies `[Me]` italic block-quote formatting before pandoc export (same as Step 2):

```powershell
cd c:\workspace\thesis
poetry run python .cursor/skills/clean-convert-transcript/convert_transcripts_to_docx.py
```

Add `--update-markdown` to also write italic formatting back to the `.md` source files.

---

## Step 4 — Update interviewee tracking table (always after cleaning)

After cleaning any transcript, always update `interviewees.xlsx` based on the cleaned transcript and assign/confirm anonymized interviewee numbering and category `x` marks.

Then explicitly notify the user to update the thesis table based on this updated workbook output.

---

## Identifying the target file

If the user names a transcript loosely (e.g. "Lauren" or "Erica"), match it to the file in `transcripts/`. If ambiguous, list the candidates and ask.

Current transcripts (as of last update):
- `Thesis interview Andreea Bulisache.md`
- `Thesis interview Erica.md`
- `Thesis interview Lauren Stokowski.md`
- `Thesis interview Tim Wiegel.md`
- `Thesis transcript Berfun Goodwin.md`
- `Thesis Transcript Erik Hilhorst.md`
- `Thesis transcript Georgio Mosis.md`
- `Thesis transcript Jon Stephan.md`
- `Thesis transcript Maarten Mantjes.md`
- `Thesis transcript Rolf Mulder.md`
- `Thesis Transcript Scott Brinker.md`
