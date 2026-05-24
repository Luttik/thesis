---
name: atlasti
description: >
  Work with Atlas.ti qualitative coding data in Cursor. Import the live project into
  a Markdown workspace (codebook, documents, memos, quotations), assist with AI-driven
  qualitative coding, create new coded quotations, refine the coding schema, and push
  all changes back to Atlas.ti. Use when the user wants to code transcripts, add new
  quotations, refine codes, reorganize groups, or review existing codings.
---

# Atlas.ti ↔ Cursor Skill

> **Status**: Fallback/debug workflow only.
> Primary coding workflow is now QDPX-first via `.cursor/skills/qdpx/`.
> Use this SQLite path only when QDPX workflows cannot preserve a required Atlas-specific behavior.

## Purpose

This skill bridges Atlas.ti 25 and Cursor so the AI agent can:
- Read all codes, quotations, memos, and full interview text from Atlas.ti
- **Create new coded quotations** directly in Atlas.ti by annotating passages in `documents/`
- Help refine the coding schema (rename, describe, group, merge, split codes)
- Reassign codes to existing quotations
- Push all changes directly back into Atlas.ti's SQLite database

## Scripts (in this folder)

| Script | Purpose |
|---|---|
| `atlasti_import.py` | Pull Atlas.ti → `atlas-coding/` |
| `atlasti_export.py` | Push `atlas-coding/` → Atlas.ti SQLite |

## Workflow

### Step 1 — Sync the backup (hard gate, always first)

Before any AI augmentation, ensure the Atlas.ti database repo is synced to remote.
Do not run import/export until this succeeds.

```powershell
cd "C:\Users\dtlut\AppData\Roaming\Scientific Software\ATLASti.25\Libraries25"
git status --short --branch
git pull --rebase
git add .
git commit -m "Sync before AI augmentation $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
git push
```

If `git commit` reports nothing to commit, still run `git push` and confirm branch is up to date.

**Atlas startup guard (new, mandatory):**
Before opening Atlas.ti (especially after restore/recovery), check for stale working-copy DB or stale lock file:

```powershell
cd "C:\Users\dtlut\AppData\Roaming\Scientific Software\ATLASti.25\Libraries25\8b640123d5644e959a1e74917f970745"
Get-ChildItem *"_WC_"*.sqlite -ErrorAction SilentlyContinue
Get-Item "..\Library.lock" -ErrorAction SilentlyContinue
```

Why: stale `*_WC_*.sqlite` and `Library.lock` can prevent Atlas.ti from loading a project even when the restored main `.sqlite` is valid.

**Safety requirement:** do **not** delete these files automatically. Ask the researcher first and confirm the latest `Libraries25` backup commit was created. Deleting them before backup commit can remove recoverable Atlas working state.

**Mandatory gate (do not skip):**
1. Run `git status --short --branch` in `Libraries25`.
2. If there are tracked or untracked changes, run `git add . && git commit -m "Sync before AI augmentation YYYY-MM-DD HH:MM"`.
3. Attempt `git push` and record the outcome in the session notes. If push fails due auth/remote issues, still proceed only after the local commit succeeds.

### Step 2 — Import from Atlas.ti

```powershell
python .cursor/skills/atlasti/atlasti_import.py
```

This writes to `atlas-coding/`:
- `codebook.md` — all 200+ codes with names, groups, usage counts, and example quotations
- `memos.md` — researcher analytical notes
- `documents/[Name].md` — full interview text (direct from Atlas.ti's content store)
- `quotations/[Name].md` — all coded segments per document
- `.meta/import.json` — import metadata and any warnings

### Step 3 — Read context (agent: do this before every coding task)

**Always re-run the import before making any edits.** The `atlas-coding/` folder is a generated snapshot — it becomes stale as soon as Atlas.ti is used directly. Never edit based on an old snapshot.

```powershell
python .cursor/skills/atlasti/atlasti_import.py
```

Then read in this order:

1. `atlas-coding/codebook.md` — understand the full coding schema
2. `atlas-coding/memos.md` — understand the researcher's analytical direction
3. `atlas-coding/quotations/[relevant doc].md` — see existing coding patterns
4. `atlas-coding/documents/[relevant doc].md` — read full interview text

**Coverage parity check** — before coding, compare quotation *density* across all documents. Some interviews span two sessions and are 2–3× longer, so raw quotation counts are misleading. Normalize by the number of **interviewee words** (lines starting with `[Them]` or `Them:`), which handles both transcript formats and is not inflated by `<!-- seg -->` markers or annotation blocks:

```powershell
# Quotes per 1000 interviewee words (normalized coverage)
Get-ChildItem atlas-coding\quotations\*.md | ForEach-Object {
    $docName = $_.BaseName
    $quotes  = (Select-String -Path $_.FullName -Pattern "^## Quotation").Count
    # Prefer the (hash) live document if a duplicate exists
    $docFile = Get-ChildItem "atlas-coding\documents\$docName*.md" |
               Sort-Object Name -Descending | Select-Object -First 1
    if ($docFile) {
        $words = (Get-Content $docFile.FullName |
                  Where-Object { $_ -match "^\[Them\]|^Them:" } |
                  ForEach-Object { ($_ -split "\s+").Count } |
                  Measure-Object -Sum).Sum
        $density = if ($words -gt 0) { [math]::Round($quotes / $words * 1000, 1) } else { "n/a" }
        "{0,-50} {1,3} quotes / {2,5} words = {3} q/1000w" -f $docName, $quotes, $words, $density
    }
}
```

If one document's density is substantially lower than the others, it needs a full coding pass. A document with two interviews will naturally have more total words — the density metric accounts for this automatically.

### Step 4 — Coding work (what the agent can do)

**Refine codes** — edit `codebook.md`:
- Change a `## Code Name` heading → renames the code in Atlas.ti
- Fill in `**Description**: ` → adds a definition to the code
- Change `**Group**: ` to an existing group name → reassigns group membership

**Edit memos** — edit `memos.md`:
- Freely rewrite the body text under any `## Memo Name` heading
- Preserve the `<!-- id: HEX -->` anchor on the line after the heading

**Reassign codes to quotations** — edit `quotations/[Doc].md`:
- Add or remove code names from the `**Codes**: ` line
- Use exact code names as they appear in backticks: `` `Code Name` ``
- Quoted text (blockquotes) is read-only

**Create new quotations** — annotate passages in `documents/[Doc].md`:

Wrap any passage with `<!-- quote -->` / `<!-- /quote -->` tags:

```markdown
<!-- quote: `Code Name A`, `Code Name B` -->
Exact verbatim text copied from below a <!-- seg:N --> marker.
<!-- /quote -->
```

**Batch-annotating many segments (recommended for large coding passes)**

When adding more than a handful of annotations, use a Python script rather than StrReplace. StrReplace fails silently on smart quotes; a script reads exact bytes and inserts safely.

There are two annotation modes:

**Mode A — full paragraph quote** (one quotation per paragraph, starting with `[Them]`):
```python
filepath = r"atlas-coding\documents\[Doc (hash)].md"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

seg_lines: dict[int, int] = {}
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("<!-- seg:") and stripped.endswith(" -->"):
        try:
            seg_lines[int(stripped[9:-4])] = i
        except ValueError:
            pass

def get_paragraph_text(seg_num: int) -> str:
    """Return the first non-empty, non-comment line after the segment marker."""
    for i in range(seg_lines[seg_num] + 1, seg_lines[seg_num] + 10):
        line = lines[i].rstrip("\n").rstrip("\r")
        if line and not line.startswith("<!--"):
            return line
    return ""

# (seg_number, codes_string) — codes must match codebook headings exactly
ANNOTATIONS = [
    (88,  "`Code A`, `Code B`"),
    (113, "`Code C`"),
]

insertions = []
for seg_num, codes in ANNOTATIONS:
    text = get_paragraph_text(seg_num)
    if text:
        block = f"<!-- quote: {codes} -->\n{text}\n<!-- /quote -->\n"
        insertions.append((seg_lines[seg_num] + 1, block))

for idx, block in sorted(insertions, key=lambda x: x[0], reverse=True):
    lines.insert(idx, block)

with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(lines)
```

**Mode B — sub-phrase quote** (multiple distinct quotations from the same paragraph, each at a precise character offset). This is the preferred mode for dense coding — it creates separate quotation objects per phrase, matching the density of native Atlas.ti coding:

```python
filepath = r"atlas-coding\documents\[Doc (hash)].md"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# (verbatim_phrase, codes_string) — phrase must appear verbatim in the document
# Each phrase gets its own quotation object in Atlas.ti (distinct character offsets)
PHRASE_ANNOTATIONS = [
    ("it's just automation",           "`automation v.s. augmentation`"),
    ("agentic AI is a bit of a hype",  "`dismissing agentic AI as hype`"),
    ("we can really get things going",  "`Benefit: Agentic AI increases speed`"),
]

blocks = []
for phrase, codes in PHRASE_ANNOTATIONS:
    if phrase in content:
        blocks.append(f"<!-- quote: {codes} -->\n{phrase}\n<!-- /quote -->\n\n")
    else:
        print(f"WARNING: phrase not found: {phrase!r}")

# Append all blocks at the end of the file (export script searches the full text)
with open(filepath, "a", encoding="utf-8") as f:
    f.writelines(blocks)
```

Key rule for sub-phrase annotations: the phrase must appear **exactly once** in the document. If it appears in multiple paragraphs, the export script will always match the **first** occurrence. Choose phrases that are unique or distinctive enough to identify the right passage.

Always run `--dry-run` after to verify the expected count of new quotations.

**Multi-pass section-by-section review strategy**

For comprehensive coding of an interview, use at least two passes:

1. **First pass (broad)** — scan the full document for substantive `[Them]` paragraphs and add full-paragraph annotations for all clearly relevant passages. Batch-annotate with Mode A above. Aim for parity with other documents.
2. **Second pass (sub-phrase)** — go back through each coded paragraph and identify individual sentences or key phrases that deserve their own quotation object. Use Mode B (sub-phrase) annotations. Each distinct analytical point in a long paragraph should become its own quotation with its own code. A paragraph with 4 distinct ideas → 4 sub-phrase annotation blocks → 4 separate quotation objects in Atlas.ti.
3. **Third pass (gap check)** — read through the document again section by section, comparing each segment against `quotations/[doc].md` to find passages that were skipped. Focus on:
   - Short but analytically dense single-line paragraphs that are easy to overlook
   - Transition paragraphs where interviewee summarises or names a concept
   - Passages near the end of the interview (often contain synthesis, reflection, or new angles)
4. **Fourth pass (thematic)** — scan by code rather than by document position. For each important code, ask: is the full range of what this interviewee said about this theme captured?

Run the coverage parity check (Step 3) after each pass to track progress.

**Critical rules for new quotations:**
1. **Copy text verbatim** — the export script finds the passage by substring search. Apostrophe and quote variants (`'` vs `'` vs `'`, `"` vs `"`) are normalized automatically, so those differences are tolerated. Any other difference — whitespace, spelling — will cause the annotation to be skipped with an error.
2. **Full-paragraph OR sub-phrase quotes are both supported.** The export script does a substring search over all paragraph text, so the verbatim text can be:
   - The full paragraph line starting from `[Them]` (creates one quotation covering the entire paragraph)
   - A specific phrase from within a paragraph, **without** the `[Them]` prefix (creates a sub-paragraph quotation at the exact character offsets of that phrase — this is the preferred way to achieve high quotation density)
3. **Sub-phrase uniqueness** — if quoting a sub-phrase rather than the full paragraph, ensure the phrase appears **exactly once** in the document. The export script always matches the **first** occurrence. If a phrase is not unique, quote a longer context so it becomes unique.
4. **Each annotation block creates its own quotation object** — two annotation blocks with different phrases (even within the same paragraph) produce two separate quotation objects in Atlas.ti with distinct character offsets. Use this to code individual sentences or key phrases as separate quotations, achieving the same density as native Atlas.ti coding.
5. **Smart quotes in file edits** — the transcripts use Unicode smart apostrophes (`'` U+2019) and ellipsis (`…` U+2026). The IDE StrReplace tool will fail silently on these. When editing the document file programmatically, always use Python with `encoding="utf-8"` and read the exact bytes from the file rather than typing quotes by hand.
6. **Code names must match exactly** — copy from `codebook.md` headings, including capitalisation and punctuation.
7. **Do not edit `<!-- seg:N -->` markers** — these are used to build the paragraph list. If they are removed or changed the lookup will fail.
8. **Multi-paragraph quotes** are supported — the text can span multiple `<!-- seg -->` paragraphs; just ensure it matches continuously across them.
9. **Fallback documents** (those with a warning about segment numbers being unreliable) cannot have new quotations exported — annotate them as suggestions only.
10. **No speaker tags in quote text** — when creating new quotations, quote substantive text only (exclude `[Them]` / `Them:` speaker prefixes from the `text` span).

### Step 4.5 — Post-apply verification (mandatory)

After creating or updating quotations via deterministic ops, always run a structural verification before finishing:

```powershell
python .cursor/skills/atlasti/verify_quote_ops.py --ops atlas-coding/quote-ops-<doc>.json
```

Pass criteria:
- `verified operations: N/N`
- `errors: 0` (or no error section)

If verification fails, fix the failing operations and rerun verification until all pass.

**What the agent cannot do directly** (requires Atlas.ti's UI):
- Create new code groups (create the group in Atlas.ti first, then reassign codes here)
- New quotation boundaries for documents that failed AML decoding (see fallback warning in document header)

**Auto-created by the export script:**
- Any code name referenced in a `<!-- quote -->` annotation that does not yet exist in Atlas.ti is **automatically created** as a new top-level code during export. No manual step required.
- The export is **idempotent**: re-running it will not create duplicate quotations; it detects already-existing quotations by position and only adds missing code links.

**Duplicate document names (hash suffix):** Atlas.ti sometimes imports the same interview twice, giving the second copy a name like `Document Name (4ba6ab14)`. The 8-character hex suffix is the **first 8 characters of that document's Atlas.ti GUID** — it is unique to this project and this document, not a generic pattern. The document **without** the suffix has `Documents.ProjectId = ZERO_GUID` (soft-deleted / ghost). The one **with** the suffix is the live document. Always annotate the `(hash)` version — that is the file the export script will target. The export script filters soft-deleted documents automatically.  

**Ghost document annotations must be fully stripped:** The `strip_ghost_annotations.py` pattern and the export script's `_QUOTE_BLOCK_RE` regex both use `[^>]+?` for the codes group. Any annotation left in the ghost document will be processed against the active document's layer with wrong paragraph positions. After adding new codes, re-run a dry-run to confirm 0 new quotations are detected from the ghost file.

**Verbatim text must come from the document file, never typed manually:** The import script preserves the exact Unicode characters Atlas.ti stores (smart quotes U+2018/U+2019, ellipsis U+2026, etc.). Always copy verbatim text directly from the `.md` file in `atlas-coding/documents/` — never type it by hand or generate it from memory. The export script normalizes apostrophes and quotes before matching, so ASCII `'` will find `'` and vice versa, but other character differences (e.g., wrong paragraph structure) will still fail.

**Location mapping is document-specific and auto-calibrated:** Atlas.ti stores quotation locations with per-document conventions (`StartElementId`, interval deltas, offset shifts). Do not assume a global paragraph offset. `atlasti_export.py` calibrates these rules from existing quotations for each document and prints the calibration in self-check. Always run strict self-check (below) and abort on any mapping error.

## Soft-delete mechanism

Atlas.ti does **not** have an `IsDeleted` column. When a code is deleted via the UI, Atlas.ti
orphans the row by setting `Tags.ProjectId` to the zero GUID
(`00000000000000000000000000000000`) while leaving the row in the database.

- **Live code**: `Tags.ProjectId = <active project UUID>`
- **Deleted code**: `Tags.ProjectId = 00000000000000000000000000000000`

The active project UUID can be found with:
```sql
SELECT hex(Id) FROM Projects LIMIT 1;
```

The import script filters these out with `AND hex(t.ProjectId) != '00000000000000000000000000000000'`
in the `get_codes()` query, so deleted codes never appear in `codebook.md`.

This same pattern applies to any entity type that has a `ProjectId` foreign key in its table
(Tags, TagGroups, Quotations, Memos, Documents). Always filter on a non-zero `ProjectId`
when querying those tables.

### Step 5 — Export back to Atlas.ti

1. **Close Atlas.ti** (required — it holds a write lock on the SQLite)
2. Run dry-run first (strict self-check is on by default):

```powershell
python .cursor/skills/atlasti/atlasti_export.py --dry-run
```

3. If dry-run has any self-check errors, fix annotations before writing.
4. Run the real export:

```powershell
python .cursor/skills/atlasti/atlasti_export.py
```

If you intentionally need to bypass strict abort behavior for a one-off recovery, use `--skip-strict-self-check` explicitly and document why.

5. Re-import immediately and verify expected quotation/code changes:

```powershell
python .cursor/skills/atlasti/atlasti_import.py
```

6. Sync the Atlas backup repo again (post-write snapshot):

```powershell
cd "C:\Users\dtlut\AppData\Roaming\Scientific Software\ATLASti.25\Libraries25"
git add .
git commit -m "Sync after AI augmentation $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
git push
```

7. **Reopen Atlas.ti** — changes appear immediately

If Atlas.ti fails to open after export or restore, run the Atlas startup guard above and ask the researcher before deleting stale `*_WC_*.sqlite` / `Library.lock`. Only proceed after backup commit confirmation, then retry before attempting another DB restore.

## File Format Reference

### `codebook.md` code entry

```markdown
### Code Name
<!-- id: HEX32CHARS -->
**Group**: Group Name
**Used in**: N quotation(s)
**Description**: Your definition here — edit this freely.
**Example**:
> Quoted text...
  — *Document Name*
**Related codes**: `Other Code` (is associated with)
```

- Edit: heading, **Description**, **Group**
- Do not edit: `<!-- id -->` anchor, **Used in**, **Example**, **Related codes**

### `memos.md` memo entry

```markdown
## Memo Title
<!-- id: HEX32CHARS -->

Memo text — edit freely.
```

### `quotations/[Doc].md` quotation entry

```markdown
## Quotation N
<!-- id: HEX32CHARS -->
**Codes**: `Code A`, `Code B`

> Quoted text — read-only.
```

- Edit: the `**Codes**:` line only
- Do not edit: `<!-- id -->`, quoted text

### `documents/[Doc].md` — new quotation annotations

Each paragraph is preceded by a `<!-- seg:N -->` marker (0-based, N+1 = Atlas.ti paragraph number).
Add annotations to code new passages:

```markdown
<!-- seg:71 -->
<!-- quote: `Code Name A`, `Code Name B` -->
Exact verbatim text from the paragraph below.
<!-- /quote -->
Them: Full paragraph text as stored in Atlas.ti...

<!-- seg:72 -->
Next paragraph...
```

The annotation can appear before OR after the `<!-- seg:N -->` marker, but the quoted text
must exist verbatim somewhere in the document file. The export script searches the full
document for the exact text to determine paragraph number and character offsets.

## Key Paths

| Item | Path |
|---|---|
| Live Atlas.ti SQLite | `%APPDATA%\Scientific Software\ATLASti.25\Libraries25\8b640123...\*.sqlite` |
| Backup git repo | `%APPDATA%\Scientific Software\ATLASti.25\Libraries25` |
| Markdown workspace | `atlas-coding/` (workspace root) |
| Import script | `.cursor/skills/atlasti/atlasti_import.py` |
| Export script | `.cursor/skills/atlasti/atlasti_export.py` |

## Safety

- **Always sync the Windows `Libraries25` backup repo before and after augmentation**
- **Treat strict self-check as mandatory**: it is enabled by default; only bypass with `--skip-strict-self-check` when you intentionally accept risk
- **Atlas.ti must be closed before running export**; script aborts if process is running
- **Never hand-edit SQLite for routine coding**; use `atlasti_export.py` and keep DB surgery for one-off repairs with explicit validation
