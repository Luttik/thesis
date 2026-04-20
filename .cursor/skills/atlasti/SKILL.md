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

### Step 1 — Sync the backup (always first)

Before any AI augmentation, ensure the Atlas.ti database is pushed to the backup repo:

```powershell
cd "C:\Users\dtlut\AppData\Roaming\Scientific Software\ATLASti.25\Libraries25"
git add .
git commit -m "Sync before AI augmentation $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
git push
```

If the working tree is already clean, confirm with `git status` and proceed.

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

**Critical rules for new quotations:**
1. **Copy text verbatim** — the export script finds the passage by string match. Apostrophe and quote variants (`'` vs `'` vs `'`, `"` vs `"`) are normalized automatically, so those differences are tolerated. Any other difference — whitespace, spelling, wrong paragraph — will cause the annotation to be skipped with an error.
2. **Include the speaker prefix** — Atlas.ti paragraphs begin with `[Them]` or `[Me]`. Your verbatim text **must** start from the very beginning of the line, including this prefix. Quoting only a substring that appears mid-line will embed the annotation comment inside the paragraph line, corrupting the structure and causing the export to fail silently.
3. **Do not annotate mid-paragraph substrings** — if the phrase you want to quote appears in the middle of a long single-line paragraph, either quote from the start of that line or skip the annotation. There is no way to target a mid-line substring.
4. **Smart quotes in file edits** — the transcripts use Unicode smart apostrophes (`'` U+2019) and ellipsis (`…` U+2026). The IDE StrReplace tool will fail silently on these. When editing the document file programmatically, always use Python with `encoding="utf-8"` and read the exact bytes from the file rather than typing quotes by hand.
5. **Code names must match exactly** — copy from `codebook.md` headings, including capitalisation and punctuation.
6. **Do not edit `<!-- seg:N -->` markers** — these are used to resolve character positions. If they are removed or changed the lookup will fail.
7. **Multi-paragraph quotes** are supported — the text can span multiple `<!-- seg -->` paragraphs; just ensure it matches continuously across them.
8. **Fallback documents** (those with a warning about segment numbers being unreliable) cannot have new quotations exported — annotate them as suggestions only.

**What the agent cannot do directly** (requires Atlas.ti's UI):
- Create new code groups (create the group in Atlas.ti first, then reassign codes here)
- New quotation boundaries for documents that failed AML decoding (see fallback warning in document header)

**Auto-created by the export script:**
- Any code name referenced in a `<!-- quote -->` annotation that does not yet exist in Atlas.ti is **automatically created** as a new top-level code during export. No manual step required.
- The export is **idempotent**: re-running it will not create duplicate quotations; it detects already-existing quotations by position and only adds missing code links.

**Duplicate document names (hash suffix):** Atlas.ti sometimes imports the same interview twice, giving the second copy a name like `Document Name (4ba6ab14)`. The 8-character hex suffix is the **first 8 characters of that document's Atlas.ti GUID** — it is unique to this project and this document, not a generic pattern. The document **without** the suffix has `Documents.ProjectId = ZERO_GUID` (soft-deleted / ghost). The one **with** the suffix is the live document. Always annotate the `(hash)` version — that is the file the export script will target. The export script filters soft-deleted documents automatically.  

**Ghost document annotations must be fully stripped:** The `strip_ghost_annotations.py` pattern and the export script's `_QUOTE_BLOCK_RE` regex both use `[^>]+?` for the codes group. Any annotation left in the ghost document will be processed against the active document's layer with wrong paragraph positions. After adding new codes, re-run a dry-run to confirm 0 new quotations are detected from the ghost file.

**Verbatim text must come from the document file, never typed manually:** The import script preserves the exact Unicode characters Atlas.ti stores (smart quotes U+2018/U+2019, ellipsis U+2026, etc.). Always copy verbatim text directly from the `.md` file in `atlas-coding/documents/` — never type it by hand or generate it from memory. The export script normalizes apostrophes and quotes before matching, so ASCII `'` will find `'` and vice versa, but other character differences (e.g., wrong paragraph structure) will still fail.

**Paragraph offset is document-specific:** Atlas.ti's `StartParagraphNumber` is 1-based, but `decode_aml_paragraphs` may silently drop structural paragraphs from the start of the raw AML binary. This means our `paragraphs[0]` does not always correspond to Atlas.ti paragraph 1. The offset must be calibrated for each document by finding one existing quotation, looking up its `StartParagraphNumber` in the database, and comparing it to the index returned by `find_text_in_paragraphs` for the same text. For this project: Berfun/Andreea use offset `+1`, Lauren Stokowski `(4ba6ab14)` uses offset `+3`. The export script hard-codes `+3` for the current project. If a new document is added, verify the offset before exporting quotations.

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
2. Run the export:

```powershell
python .cursor/skills/atlasti/atlasti_export.py --dry-run   # preview changes
python .cursor/skills/atlasti/atlasti_export.py             # write changes
```

3. **Reopen Atlas.ti** — changes appear immediately

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

- **Always git-push the backup before AI augmentation** (enforced by `atlasti-backup-sync.mdc` rule)
- **Atlas.ti must be closed before running the export script**
- Use `--dry-run` to preview what will change before committing
- The export script checks for a running Atlas.ti process and aborts if found
