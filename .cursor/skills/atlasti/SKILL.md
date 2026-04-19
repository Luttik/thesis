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

**Always read in this order:**

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
1. **Copy text verbatim** — the export script finds the passage by exact string match. Any difference in whitespace, punctuation, or apostrophe style (e.g. `'` vs `'`) will cause the annotation to be skipped with an error.
2. **Code names must match exactly** — copy from `codebook.md` headings, including capitalisation and punctuation.
3. **Do not edit `<!-- seg:N -->` markers** — these are used to resolve character positions. If they are removed or changed the lookup will fail.
4. **Multi-paragraph quotes** are supported — the text can span multiple `<!-- seg -->` paragraphs; just ensure it matches continuously across them.
5. **Fallback documents** (those with a warning about segment numbers being unreliable) cannot have new quotations exported — annotate them as suggestions only.

**What the agent cannot do directly** (requires Atlas.ti's UI):
- Create new code groups (create the group in Atlas.ti first, then reassign codes here)
- New quotation boundaries for documents that failed AML decoding (see fallback warning in document header)

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
