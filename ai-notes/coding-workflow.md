# Coding Workflow (QDPX-First)

This project now uses a QDPX-first qualitative coding workflow.

## Source of truth

- Source archive: `*.qdpx` file in workspace root
- Working snapshot: `qdpx-coding/`
- Verification snapshot: `qdpx-coding-verify/`

## Standard runbook

1. Import full project to markdown workspace:

```powershell
python .cursor/skills/qdpx/qdpx_import.py --qdpx "Thesis.qdpx" --out qdpx-coding
```

2. Edit coding workspace:
- `qdpx-coding/codebook.md` (code names and descriptions)
- `qdpx-coding/memos.md` (memo titles and bodies)
- `qdpx-coding/quotations/*.md` (quotation `**Codes**:` lines)

3. Export to a new QDPX file (never overwrite original):

```powershell
python .cursor/skills/qdpx/qdpx_export.py --base "Thesis.qdpx" --in qdpx-coding --out "Thesis-updated.qdpx"
```

4. Validate integrity and no-loss constraints:

```powershell
python .cursor/skills/qdpx/qdpx_validate.py --baseline "Thesis.qdpx" --qdpx "Thesis-updated.qdpx"
```

5. Review structural deltas:

```powershell
python .cursor/skills/qdpx/qdpx_diff.py --old "Thesis.qdpx" --new "Thesis-updated.qdpx"
```

6. Re-import output for spot checks:

```powershell
python .cursor/skills/qdpx/qdpx_import.py --qdpx "Thesis-updated.qdpx" --out qdpx-coding-verify
```

## Guardrails

- Full-project only (no doc-scoped export/reset).
- Stop immediately if validation reports errors.
- Treat unexpected count drops as potential data loss.

## Optional: merge two QDPX files

Use this when coding was done in parallel and needs to be unified:

```powershell
python .cursor/skills/qdpx/qdpx_merge.py --base "Thesis-manual.qdpx" --incoming "Thesis-erik.qdpx" --out "Thesis-merged.qdpx"
```

Then run validate + diff on `Thesis-merged.qdpx`.

## Atlas SQLite fallback

Use `.cursor/skills/atlasti/` scripts only for recovery/debug or Atlas-specific behavior not supported in QDPX.
