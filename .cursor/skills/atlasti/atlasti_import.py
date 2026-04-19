#!/usr/bin/env python3
"""atlasti_import.py — Pull live Atlas.ti SQLite into atlas-coding/ Markdown workspace.

Usage:
    python .cursor/skills/atlasti/atlasti_import.py
"""

import json
import re
import sqlite3
import struct
from datetime import datetime
from pathlib import Path

import typer

app = typer.Typer(help="Import Atlas.ti project into Cursor-readable Markdown workspace.")

# ── Paths ────────────────────────────────────────────────────────────────────

ATLAS_LIB_BASE = (
    Path.home() / "AppData" / "Roaming" / "Scientific Software" / "ATLASti.25" / "Libraries25"
)
LOCAL_CONTENTS = ATLAS_LIB_BASE / "Local" / "Contents"

SKILL_DIR = Path(__file__).parent
WORKSPACE_ROOT = SKILL_DIR.parent.parent.parent  # .cursor/skills/atlasti → workspace
ATLAS_CODING_DIR = WORKSPACE_ROOT / "atlas-coding"
TRANSCRIPTS_DIR = WORKSPACE_ROOT / "transcripts"

# ── AML binary decoder ───────────────────────────────────────────────────────

AML_MAGIC = b"\x99\x40\xa8\xac\x06\x70\x11\x49"
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_MULTI_SPACE = re.compile(r"  +")


_AML_SENTINEL_RE = re.compile(r"[\ufffe\uffff].*$", re.DOTALL)  # stop at AML binary markers
_AML_LEAD_RE = re.compile(r"^[^\x20-\x7e\u2029\r\n]*")  # strip leading non-ASCII garbage


def decode_aml(data: bytes) -> str:
    """Extract plain text from Atlas.ti AML binary blob.

    Format: [16-byte header][8-byte int64 text_start][offset table...]
    At text_start: 16-byte GUID + null padding, then UTF-16 LE text terminated by
    U+FFFE/U+FFFF sentinel markers.

    Magic bytes vary across Atlas.ti versions; we rely solely on the offset structure.
    """
    if not data or len(data) < 24:
        return ""
    text_start = struct.unpack_from("<q", data, 16)[0]
    if text_start < 24 or text_start >= len(data):
        return ""

    raw = data[text_start:].decode("utf-16-le", errors="ignore")

    # Skip the 16-byte GUID (= 8 UTF-16 chars) at the start of the text region
    raw = raw[8:]

    # Strip any remaining leading non-printable/non-ASCII chars (null padding etc.)
    raw = _AML_LEAD_RE.sub("", raw)

    # Cut at AML binary sentinel markers (U+FFFE or U+FFFF signal end of text)
    raw = _AML_SENTINEL_RE.sub("", raw)

    # \u2029 is Atlas.ti paragraph separator → blank line
    raw = raw.replace("\u2029", "\n\n")
    raw = _CTRL_RE.sub(" ", raw)
    raw = _MULTI_SPACE.sub(" ", raw)

    # Strip trailing lines that are AML formatting artifacts:
    # lines consisting only of 1-3 char tokens (e.g. "y x x", "w w")
    lines = raw.splitlines()
    while lines:
        stripped = lines[-1].strip()
        tokens = stripped.split()
        if stripped and all(len(t) <= 3 for t in tokens) and len(tokens) <= 6:
            lines.pop()
        else:
            break

    return "\n".join(lines).strip()


def read_aml_file(location: str) -> str:
    """Read an AML content file by its GUID location string."""
    path = LOCAL_CONTENTS / location
    if not path.exists():
        return ""
    try:
        return decode_aml(path.read_bytes())
    except Exception:
        return ""


# ── SQLite helpers ───────────────────────────────────────────────────────────

ZERO_GUID = b"\x00" * 16


def find_live_sqlite() -> Path:
    """Auto-detect the live Atlas.ti project SQLite (excludes _B_ and _WC_ backups)."""
    for lib_dir in ATLAS_LIB_BASE.iterdir():
        if not lib_dir.is_dir() or lib_dir.name == "Local":
            continue
        for f in lib_dir.glob("*.sqlite"):
            if "_B_" not in f.name and "_WC_" not in f.name:
                return f
    raise FileNotFoundError(
        f"No live Atlas.ti project SQLite found under {ATLAS_LIB_BASE}.\n"
        "Make sure Atlas.ti 25 is installed and a project has been opened at least once."
    )


def hex_id(b: bytes) -> str:
    return b.hex() if b else ""


# ── Data extraction ──────────────────────────────────────────────────────────


def _fetch_entity_comment(cur: sqlite3.Cursor, entity_id: bytes) -> str:
    """Return decoded comment text for any entity via the Media→Contents chain."""
    cur.execute(
        """
        SELECT c2.Data
        FROM Entities e
        JOIN Comments c  ON e.CommentId = c.Id
        JOIN Media m     ON c.MediumId  = m.Id
        JOIN MediaContentHandles mch ON m.CurrentContentHandleId = mch.Id
        JOIN Contents c2 ON mch.ContentId = c2.Id
        WHERE e.Id = ? AND e.CommentId != ?
        """,
        (entity_id, ZERO_GUID),
    )
    row = cur.fetchone()
    return decode_aml(row[0]) if row and row[0] else ""


def get_project_info(cur: sqlite3.Cursor) -> dict:
    """Read project name via Projects→Entities join; counts derived from data."""
    cur.execute(
        "SELECT e.Name FROM Projects p JOIN Entities e ON p.Id = e.Id LIMIT 1"
    )
    row = cur.fetchone()
    return {"name": (row[0] if row and row[0] else "Atlas.ti Project")}


def get_groups(cur: sqlite3.Cursor) -> dict[str, str]:
    """Return {tag_hex_id: group_name}."""
    cur.execute(
        """
        SELECT hex(tgt.TagId), e.Name
        FROM TagGroupTags tgt
        JOIN TagGroups    tg  ON tgt.TagGroupId = tg.Id
        JOIN Entities     e   ON tg.Id           = e.Id
        WHERE e.Name IS NOT NULL
        """
    )
    return {row[0].upper(): row[1] for row in cur.fetchall()}


def get_codes(cur: sqlite3.Cursor) -> list[dict]:
    """Return all user codes with name, description, parent, group, usage count."""
    groups = get_groups(cur)

    cur.execute(
        """
        SELECT t.Id, e.Name, hex(t.ParentId), e.CommentId
        FROM Tags t
        JOIN Entities e ON t.Id = e.Id
        WHERE t.TagType = 0 AND e.Name IS NOT NULL AND e.Name != ''
        ORDER BY e.Name
        """
    )
    rows = cur.fetchall()

    # Quotation counts per code
    cur.execute(
        """
        SELECT hex(lnk.SourceId), COUNT(*)
        FROM Links lnk
        JOIN Tags t ON lnk.SourceId = t.Id
        GROUP BY lnk.SourceId
        """
    )
    usage = {row[0].upper(): row[1] for row in cur.fetchall()}

    # Parent id → name map
    cur.execute("SELECT hex(t.Id), e.Name FROM Tags t JOIN Entities e ON t.Id = e.Id")
    id_to_name = {row[0].upper(): row[1] for row in cur.fetchall()}

    codes = []
    for tag_id, name, parent_hex, comment_id in rows:
        hid = tag_id.hex().upper()
        description = _fetch_entity_comment(cur, tag_id) if comment_id != ZERO_GUID else ""
        parent_name = id_to_name.get(parent_hex.upper(), "") if parent_hex else ""
        codes.append(
            {
                "id": hid,
                "name": name,
                "description": description,
                "parent": parent_name,
                "group": groups.get(hid, ""),
                "usage": usage.get(hid, 0),
            }
        )
    return codes


def get_quotations(cur: sqlite3.Cursor) -> list[dict]:
    """Return all quotations with plain text, codes, and document name."""
    # tag → quotation links
    cur.execute(
        """
        SELECT hex(lnk.TargetId), hex(lnk.SourceId)
        FROM Links lnk
        JOIN Tags t ON lnk.SourceId = t.Id
        """
    )
    quot_to_codes: dict[str, list[str]] = {}
    for quot_hid, code_hid in cur.fetchall():
        quot_to_codes.setdefault(quot_hid.upper(), []).append(code_hid.upper())

    # code id → name
    cur.execute("SELECT hex(t.Id), e.Name FROM Tags t JOIN Entities e ON t.Id = e.Id")
    id_to_name = {row[0].upper(): row[1] for row in cur.fetchall()}

    cur.execute(
        """
        SELECT q.Id, q.Number, q.PlainText, e.Name
        FROM Quotations q
        JOIN Layers   l ON q.LayerId    = l.Id
        JOIN Documents d ON l.DocumentId = d.Id
        JOIN Entities  e ON d.Id         = e.Id
        ORDER BY e.Name, q.Number
        """
    )
    quotations = []
    for qid, number, plain_text, doc_name in cur.fetchall():
        hid = qid.hex().upper()
        code_ids = quot_to_codes.get(hid, [])
        code_names = [id_to_name[c] for c in code_ids if c in id_to_name]
        quotations.append(
            {
                "id": hid,
                "number": number,
                "text": (plain_text or "").strip(),
                "document": doc_name or "Unknown",
                "codes": sorted(code_names),
            }
        )
    return quotations


def get_memos(cur: sqlite3.Cursor) -> list[dict]:
    """Return all memos with name and decoded text content."""
    cur.execute(
        """
        SELECT mo.Id, e.Name, c.Data
        FROM Memos mo
        JOIN Entities e ON mo.Id = e.Id
        LEFT JOIN Media m ON mo.MediumId = m.Id
        LEFT JOIN MediaContentHandles mch ON m.CurrentContentHandleId = mch.Id
        LEFT JOIN Contents c ON mch.ContentId = c.Id
        ORDER BY e.Name
        """
    )
    memos = []
    for mid, name, data in cur.fetchall():
        memos.append(
            {
                "id": mid.hex().upper(),
                "name": name or "Untitled memo",
                "text": decode_aml(data) if data else "",
            }
        )
    return memos


def get_documents(cur: sqlite3.Cursor) -> list[dict]:
    """Return documents with name and content file location."""
    cur.execute(
        """
        SELECT d.Id, e.Name, mch.Location
        FROM Documents d
        JOIN Entities e ON d.Id = e.Id
        LEFT JOIN Media m ON d.MediumId = m.Id
        LEFT JOIN MediaContentHandles mch ON m.CurrentContentHandleId = mch.Id
        ORDER BY e.Name
        """
    )
    seen: set[str] = set()
    docs = []
    for did, name, location in cur.fetchall():
        doc_name = name or "Untitled"
        if doc_name in seen:
            doc_name = f"{doc_name} ({did.hex()[:8]})"
        seen.add(doc_name)
        docs.append(
            {
                "id": did.hex().upper(),
                "name": doc_name,
                "location": location or "",
            }
        )
    return docs


# ── Markdown writers ─────────────────────────────────────────────────────────


def write_codebook(
    codes: list[dict],
    quotations: list[dict],
    documents: list[dict],
    project: dict,
    out_dir: Path,
) -> None:
    """Write atlas-coding/codebook.md — the primary agent reference."""
    # Build example map: code_name → first quotation text
    examples: dict[str, tuple[str, str]] = {}  # code_name → (text, doc)
    for q in quotations:
        for c in q["codes"]:
            if c not in examples:
                examples[c] = (q["text"], q["document"])

    lines = [
        f"# Codebook — {project.get('name', 'Atlas.ti Project')}",
        f"*Imported {datetime.now().strftime('%Y-%m-%d %H:%M')}*  ",
        f"{len(codes)} codes · {len(quotations)} quotations · {len(documents)} documents",
        "",
        "> **Agent instructions**: Read this file first before doing any coding work.",
        "> Edit `Description` fields to refine definitions. Do not edit `<!-- id -->` anchors.",
        "",
        "---",
        "",
    ]

    # Group codes by their group name
    grouped: dict[str, list[dict]] = {}
    for c in codes:
        grouped.setdefault(c["group"] or "Ungrouped", []).append(c)

    for group_name, group_codes in sorted(grouped.items()):
        lines += [f"## Group: {group_name}", ""]
        for c in group_codes:
            lines.append(f"### {c['name']}")
            lines.append(f"<!-- id: {c['id']} -->")
            if c["parent"]:
                lines.append(f"**Parent code**: `{c['parent']}`  ")
            lines.append(f"**Used in**: {c['usage']} quotation(s)  ")
            if c["description"]:
                lines.append(f"**Description**: {c['description']}  ")
            else:
                lines.append("**Description**: *(not set)*  ")
            if c["name"] in examples:
                ex_text, ex_doc = examples[c["name"]]
                short = ex_text[:200] + ("…" if len(ex_text) > 200 else "")
                lines += [
                    "**Example**:",
                    f"> {short}",
                    f"  — *{ex_doc}*",
                ]
            lines.append("")

    (out_dir / "codebook.md").write_text("\n".join(lines), encoding="utf-8")


def write_memos(memos: list[dict], out_dir: Path) -> None:
    lines = [
        "# Memos",
        "",
        "> **Agent instructions**: Edit memo text freely. Do not edit `<!-- id -->` anchors.",
        "",
    ]
    for m in memos:
        lines += [
            f"## {m['name']}",
            f"<!-- id: {m['id']} -->",
            "",
            m["text"] or "*(empty)*",
            "",
            "---",
            "",
        ]
    (out_dir / "memos.md").write_text("\n".join(lines), encoding="utf-8")


def write_quotations(quotations: list[dict], out_dir: Path) -> None:
    """Write one file per document under atlas-coding/quotations/."""
    quot_dir = out_dir / "quotations"
    quot_dir.mkdir(exist_ok=True)

    by_doc: dict[str, list[dict]] = {}
    for q in quotations:
        by_doc.setdefault(q["document"], []).append(q)

    for doc_name, quots in sorted(by_doc.items()):
        safe = re.sub(r'[<>:"/\\|?*]', "_", doc_name)
        lines = [
            f"# Quotations — {doc_name}",
            "",
            "> **Agent instructions**: Edit the `Codes` line to reassign codes.",
            "> Quoted text (blockquotes) is read-only — boundaries are managed by Atlas.ti.",
            "",
        ]
        for q in sorted(quots, key=lambda x: x["number"]):
            codes_str = ", ".join(f"`{c}`" for c in q["codes"]) if q["codes"] else "*(uncoded)*"
            lines += [
                f"## Quotation {q['number']}",
                f"<!-- id: {q['id']} -->",
                f"**Codes**: {codes_str}  ",
                "",
                f"> {q['text']}",
                "",
            ]
        (quot_dir / f"{safe}.md").write_text("\n".join(lines), encoding="utf-8")


def write_documents(documents: list[dict], out_dir: Path, warnings: list[str]) -> None:
    """Write full interview text under atlas-coding/documents/."""
    doc_dir = out_dir / "documents"
    doc_dir.mkdir(exist_ok=True)

    for doc in documents:
        safe = re.sub(r'[<>:"/\\|?*]', "_", doc["name"])
        text = ""

        if doc["location"]:
            text = read_aml_file(doc["location"])

        if not text:
            # Fallback: search transcripts/ for a matching file by stem similarity
            stem = Path(doc["name"]).stem.lower()
            for md in TRANSCRIPTS_DIR.glob("*.md"):
                if stem in md.stem.lower() or md.stem.lower() in stem:
                    text = md.read_text(encoding="utf-8")
                    warnings.append(
                        f"Document '{doc['name']}': used fallback transcript '{md.name}' "
                        "(AML decode failed or no content file found)"
                    )
                    break

        if not text:
            warnings.append(
                f"Document '{doc['name']}': could not extract text "
                "(no content file and no matching transcript fallback)"
            )
            text = "*(text unavailable — open document in Atlas.ti)*"

        header = [
            f"# {doc['name']}",
            "",
            "> **Read-only** — this is the interview text as stored in Atlas.ti.",
            "> To add new quotations, highlight text in Atlas.ti's document editor.",
            "",
            "---",
            "",
        ]
        (doc_dir / f"{safe}.md").write_text(
            "\n".join(header) + text, encoding="utf-8"
        )


# ── Main command ─────────────────────────────────────────────────────────────


@app.command()
def main(
    db_path: Path = typer.Option(
        None,
        "--db",
        help="Path to Atlas.ti SQLite file. Auto-detected if not provided.",
    ),
    output_dir: Path = typer.Option(
        None,
        "--out",
        help="Output directory. Defaults to <workspace>/atlas-coding/.",
    ),
) -> None:
    """Extract Atlas.ti project into a Markdown workspace for AI-assisted coding."""
    sqlite_path = db_path or find_live_sqlite()
    out_dir = output_dir or ATLAS_CODING_DIR

    typer.echo(f"Reading: {sqlite_path}")
    typer.echo(f"Writing: {out_dir}")

    out_dir.mkdir(exist_ok=True)
    (out_dir / ".meta").mkdir(exist_ok=True)

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    warnings: list[str] = []

    with typer.progressbar(length=5, label="Extracting") as progress:
        project = get_project_info(cur)
        progress.update(1)

        codes = get_codes(cur)
        progress.update(1)

        quotations = get_quotations(cur)
        progress.update(1)

        memos = get_memos(cur)
        progress.update(1)

        documents = get_documents(cur)
        progress.update(1)

    conn.close()

    with typer.progressbar(length=5, label="Writing  ") as progress:
        write_codebook(codes, quotations, documents, project, out_dir)
        progress.update(1)

        write_memos(memos, out_dir)
        progress.update(1)

        write_quotations(quotations, out_dir)
        progress.update(1)

        write_documents(documents, out_dir, warnings)
        progress.update(1)

        meta = {
            "sqlite": str(sqlite_path),
            "imported_at": datetime.now().isoformat(),
            "project": project,
            "counts": {
                "codes": len(codes),
                "quotations": len(quotations),
                "memos": len(memos),
                "documents": len(documents),
            },
            "warnings": warnings,
        }
        (out_dir / ".meta" / "import.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        progress.update(1)

    typer.echo(
        f"\nDone. Wrote {len(codes)} codes, {len(quotations)} quotations, "
        f"{len(memos)} memos, {len(documents)} documents"
    )

    if warnings:
        typer.echo(f"\n⚠  {len(warnings)} warning(s):")
        for w in warnings:
            typer.echo(f"   • {w}")

    typer.echo(f"\nWorkspace ready at: {out_dir}")
    typer.echo("Start with: atlas-coding/codebook.md")


if __name__ == "__main__":
    app()
