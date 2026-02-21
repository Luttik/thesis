# Transcripts

Interview and debrief transcripts (Markdown, `Me:` / `Them:` speaker labels).

## Cleaning workflow (Cursor + chunking)

Long transcripts are easier to clean in Cursor when split into chunks. Use this workflow:

1. **Split** (optional pre-pass with script):
   ```powershell
   poetry run python scripts/transcript_chunks.py split path/to/transcript.md --turns 90 --out-dir path/to
   ```
   Creates `transcript-part1.md`, `transcript-part2.md`, … in the same directory (or `--out-dir`). Default 90 speaker turns per chunk.

2. **Optional deterministic fix** before or after split (stutters like "I I " → "I ", and a short list of known ASR errors):
   ```powershell
   poetry run python scripts/transcript_chunks.py fix path/to/transcript.md --in-place
   ```
   Omit `--in-place` to print the result to stdout.

3. **Clean each chunk in Cursor**  
   Open each `*-part*.md` file and ask Cursor to clean it according to the project rules. The transcript-cleaning rule is in [.cursor/rules/transcript-cleaning.mdc](../.cursor/rules/transcript-cleaning.mdc). You can also use [Transcript-cleaning-instructions.md](Transcript-cleaning-instructions.md) as a prompt reference.

4. **Merge** cleaned chunks back into one file:
   ```powershell
   poetry run python scripts/transcript_chunks.py merge path/to/directory --output path/to/transcript-cleaned.md
   ```
   The script finds all `*-part*.md` files in the given directory, sorts by part number, and writes one merged file. Use `--output` to set the output path; default is `<base>-merged.md` in the same directory.

## Cleaning rules (summary)

- **Do:** Fix clear ASR errors and same-word stutters ("I I " → "I "). Keep one turn per line and consistent formatting.
- **Do not:** Remove fillers (um, like, yeah), rewrite participants’ words, or change meaning. See [Transcript-cleaning-instructions.md](Transcript-cleaning-instructions.md) for the full list.

## Script location

- **Split / merge / fix:** [scripts/transcript_chunks.py](../scripts/transcript_chunks.py) (requires Poetry: `poetry install` from repo root).
