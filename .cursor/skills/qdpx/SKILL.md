---
name: qdpx
description: >
  Primary qualitative coding workflow. Work with full-project QDPX (QDA-XML)
  files end-to-end: import -> code/recode -> context expansion -> export ->
  validate -> diff. Use this as default; keep SQLite workflow as fallback only.
---

# QDPX Full-Project Skill

## Purpose

This skill is the default coding path and is intentionally file-based.

- Source of truth: `.qdpx` archives
- Working snapshot: `qdpx-coding/`
- Scope rule: **always full project** (never doc-scoped operations)
- Safety rule: export only after validation + diff

## CLI Commands

- `qdpx_import.py` - pull `.qdpx` -> markdown workspace
- `qdpx_export.py` - apply markdown edits -> new `.qdpx`
- `qdpx_merge.py` - merge coding from one `.qdpx` into another
- `qdpx_validate.py` - integrity + no-loss checks
- `qdpx_diff.py` - compare old/new `.qdpx`
- `poetry run qdpx-dedupe-launch` - launch dedupe TUI (current terminal by default)
- `poetry run qdpx-dedupe-apply` - apply dedupe review CSV into a new `.qdpx`
- `poetry run qdpx-category-suggest` - review/assign top-level categories for uncategorised coded leaf codes

## Workflow

1) Import full project

```powershell
python .cursor/skills/qdpx/qdpx_import.py --qdpx "Thesis.qdpx" --out qdpx-coding
```

2) Edit in `qdpx-coding/`

- `codebook.md` for code name/description updates
- `memos.md` for memo body/title updates
- `quotations/*.md` for code-line reassignments

3) Coding pass strategy (enforced)

- Pass A: analytical/tighter coding
- Pass B: context expansion where quotes are too narrow
- Goal: preserve analytic precision while adding sufficient interpretive context

4) Export full project

```powershell
python .cursor/skills/qdpx/qdpx_export.py --base "Thesis.qdpx" --in qdpx-coding --out "Thesis-updated.qdpx"
```

5) Validate no-loss constraints

```powershell
python .cursor/skills/qdpx/qdpx_validate.py --baseline "Thesis.qdpx" --qdpx "Thesis-updated.qdpx"
```

6) Review structural deltas

```powershell
python .cursor/skills/qdpx/qdpx_diff.py --old "Thesis.qdpx" --new "Thesis-updated.qdpx"
```

7) Re-import updated output for spot-check

```powershell
python .cursor/skills/qdpx/qdpx_import.py --qdpx "Thesis-updated.qdpx" --out qdpx-coding-verify
```

## Code Deduplication Review (Default Launch Behavior)

When deduplication review is requested, launch the TUI via the launcher script so a
new terminal window is used by default:

```powershell
poetry run qdpx-dedupe-launch --qdpx "qdpx/Thesis (...).qdpx"
```

Use `--new-window` to request a separate terminal window/tab. If unavailable,
the launcher falls back to the current terminal.

## Hard Rules

- Never run doc-only exports/resets in this skill.
- Never overwrite the original `.qdpx`; write a new output file.
- If `qdpx_validate.py` fails, do not ship/export the result.
- If counts drop unexpectedly, treat as potential data loss and stop.
- Keep SQLite-based skill available for recovery/debug, not as primary coding path.

## Notes

- Quotations are anchored by QDA-XML character offsets (`startPosition`, `endPosition`).
- `qdpx_export.py` is full-project only and supports code/memo/quotation updates from markdown.
- IDs may change during recoding; acceptable as long as validation passes and no relevant data is lost.
