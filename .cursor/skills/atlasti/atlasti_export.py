#!/usr/bin/env python3
"""atlasti_export.py — Push atlas-coding/ Markdown changes back into the live Atlas.ti SQLite.

Editable elements:
  - Code names            (codebook.md  ## headings)
  - Code descriptions     (codebook.md  **Description**: lines)
  - Code group membership (codebook.md  **Group**: lines — reassigns to existing groups)
  - Memo text             (memos.md     body under each ## heading)
  - Quotation code lists  (quotations/  **Codes**: lines)

All changes are keyed by the <!-- id: HEX --> anchors — do NOT remove them.

Usage:
    python .cursor/skills/atlasti/atlasti_export.py
    python .cursor/skills/atlasti/atlasti_export.py --dry-run
"""

import re
import sqlite3
import struct
import subprocess
import sys
from pathlib import Path

import typer

app = typer.Typer(help="Push atlas-coding/ Markdown changes back into the live Atlas.ti SQLite.")

# ── Paths ────────────────────────────────────────────────────────────────────

ATLAS_LIB_BASE = (
    Path.home() / "AppData" / "Roaming" / "Scientific Software" / "ATLASti.25" / "Libraries25"
)

SKILL_DIR = Path(__file__).parent
WORKSPACE_ROOT = SKILL_DIR.parent.parent.parent
ATLAS_CODING_DIR = WORKSPACE_ROOT / "atlas-coding"

ZERO_GUID = b"\x00" * 16
AML_MAGIC = b"\x99\x40\xa8\xac\x06\x70\x11\x49\x9d\xb3\x64\xb9\xab\x81\x2f\xf1"

# ── Safety checks ─────────────────────────────────────────────────────────────


def check_atlasti_not_running() -> None:
    """Abort if Atlas.ti is currently running (it holds a write lock on the SQLite)."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq ATLASti*", "/NH"],
            capture_output=True, text=True,
        )
        if "ATLASti" in result.stdout:
            typer.echo(
                "ERROR: Atlas.ti appears to be running.\n"
                "Close Atlas.ti before running this export to avoid data corruption.",
                err=True,
            )
            raise typer.Exit(1)
    except FileNotFoundError:
        pass  # tasklist not available — skip check


def find_live_sqlite() -> Path:
    for lib_dir in ATLAS_LIB_BASE.iterdir():
        if not lib_dir.is_dir() or lib_dir.name == "Local":
            continue
        for f in lib_dir.glob("*.sqlite"):
            if "_B_" not in f.name and "_WC_" not in f.name:
                return f
    raise FileNotFoundError(f"No live Atlas.ti project SQLite found under {ATLAS_LIB_BASE}")


# ── AML binary builder ────────────────────────────────────────────────────────


def encode_aml(text: str) -> bytes:
    """Build a minimal AML binary blob for plain text content.

    Structure: [16-byte magic][8-byte text_start=24][8-byte GUID placeholder][UTF-16 LE text]
    This is a simplified AML suitable for descriptions and memos.
    """
    text_start = 24  # 16-byte magic + 8-byte offset
    guid_placeholder = b"\x00" * 16  # 16-byte null GUID (8 UTF-16 chars)
    text_bytes = (text.strip()).encode("utf-16-le")
    offset = struct.pack("<q", text_start)
    return AML_MAGIC + offset + guid_placeholder + text_bytes


# ── Markdown parsers ──────────────────────────────────────────────────────────

_ID_RE = re.compile(r"<!--\s*id:\s*([0-9A-Fa-f]{32})\s*-->")
_CODES_RE = re.compile(r"\*\*Codes\*\*:\s*(.*)")
_CODE_ITEM_RE = re.compile(r"`([^`]+)`")


def parse_codebook(codebook_path: Path) -> list[dict]:
    """Parse codebook.md into a list of code dicts."""
    text = codebook_path.read_text(encoding="utf-8")
    codes: list[dict] = []
    current: dict | None = None

    for line in text.splitlines():
        # New code section starts at ### heading
        if line.startswith("### "):
            if current:
                codes.append(current)
            current = {
                "name": line[4:].strip(),
                "id": None,
                "description": None,
                "group": None,
            }
            continue

        if current is None:
            continue

        m = _ID_RE.search(line)
        if m:
            current["id"] = bytes.fromhex(m.group(1))
            continue

        if line.startswith("**Group**:"):
            val = line.split(":", 1)[1].strip()
            current["group"] = val if val != "*(none)*" else ""
            continue

        if line.startswith("**Description**:"):
            val = line.split(":", 1)[1].strip()
            current["description"] = "" if val in ("*(not set)*", "") else val
            continue

    if current:
        codes.append(current)

    return [c for c in codes if c["id"]]


def parse_memos(memos_path: Path) -> list[dict]:
    """Parse memos.md into list of memo dicts with id and text."""
    text = memos_path.read_text(encoding="utf-8")
    memos: list[dict] = []
    current: dict | None = None
    body_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current and current["id"]:
                current["text"] = "\n".join(body_lines).strip()
                memos.append(current)
            current = {"name": line[3:].strip(), "id": None, "text": ""}
            body_lines = []
            continue

        if current is None:
            continue

        m = _ID_RE.search(line)
        if m:
            current["id"] = bytes.fromhex(m.group(1))
            continue

        if line.strip() == "---":
            continue

        # Skip the agent instructions comment block
        if line.startswith(">"):
            continue

        body_lines.append(line)

    if current and current["id"]:
        current["text"] = "\n".join(body_lines).strip()
        memos.append(current)

    return memos


def parse_quotations(quot_dir: Path) -> dict[bytes, list[str]]:
    """Parse all quotations/*.md files.

    Returns {quotation_id_bytes: [code_name, ...]}
    """
    result: dict[bytes, list[str]] = {}
    for md_file in quot_dir.glob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        current_id: bytes | None = None
        for line in text.splitlines():
            m = _ID_RE.search(line)
            if m:
                current_id = bytes.fromhex(m.group(1))
                continue
            if current_id and line.startswith("**Codes**:"):
                if "*(uncoded)*" in line:
                    result[current_id] = []
                else:
                    result[current_id] = _CODE_ITEM_RE.findall(line)
                current_id = None
    return result


# ── SQLite write helpers ──────────────────────────────────────────────────────


def get_existing_codes(cur: sqlite3.Cursor) -> dict[bytes, dict]:
    """Return {id_bytes: {name, description_data, comment_id, medium_id, ...}}."""
    cur.execute(
        """
        SELECT t.Id, e.Name, e.CommentId,
               cm.MediumId, mch.Id as mch_id, mch.ContentId
        FROM Tags t
        JOIN Entities e ON t.Id = e.Id
        LEFT JOIN Comments cm ON e.CommentId = cm.Id AND e.CommentId != ?
        LEFT JOIN Media m ON cm.MediumId = m.Id
        LEFT JOIN MediaContentHandles mch ON m.CurrentContentHandleId = mch.Id
        WHERE t.TagType = 0
        """,
        (ZERO_GUID,),
    )
    result = {}
    for row in cur.fetchall():
        result[row[0]] = {
            "name": row[1],
            "comment_id": row[2],
            "medium_id": row[3],
            "mch_id": row[4],
            "content_id": row[5],
        }
    return result


def get_group_map(cur: sqlite3.Cursor) -> dict[str, bytes]:
    """Return {group_name: group_id_bytes}."""
    cur.execute(
        "SELECT e.Name, tg.Id FROM TagGroups tg JOIN Entities e ON tg.Id = e.Id"
    )
    return {row[0]: row[1] for row in cur.fetchall() if row[0]}


def get_code_name_to_id(cur: sqlite3.Cursor) -> dict[str, bytes]:
    """Return {code_name: id_bytes} for all user codes."""
    cur.execute(
        "SELECT e.Name, t.Id FROM Tags t JOIN Entities e ON t.Id = e.Id WHERE t.TagType = 0"
    )
    return {row[0]: row[1] for row in cur.fetchall() if row[0]}


def get_quotation_current_codes(
    cur: sqlite3.Cursor,
) -> dict[bytes, set[bytes]]:
    """Return {quotation_id: {tag_id, ...}} for all existing code assignments."""
    cur.execute(
        "SELECT lnk.TargetId, lnk.SourceId FROM Links lnk JOIN Tags t ON lnk.SourceId = t.Id"
    )
    result: dict[bytes, set[bytes]] = {}
    for quot_id, tag_id in cur.fetchall():
        result.setdefault(quot_id, set()).add(tag_id)
    return result


def update_entity_name(cur: sqlite3.Cursor, entity_id: bytes, new_name: str) -> None:
    cur.execute("UPDATE Entities SET Name = ? WHERE Id = ?", (new_name, entity_id))


def upsert_code_description(
    conn: sqlite3.Connection,
    cur: sqlite3.Cursor,
    existing: dict,
    entity_id: bytes,
    description: str,
) -> None:
    """Update or create the AML content for a code's description."""
    aml_data = encode_aml(description)

    if existing.get("content_id"):
        # Update existing Contents row
        cur.execute(
            "UPDATE Contents SET Data = ? WHERE Id = ?",
            (aml_data, existing["content_id"]),
        )
    else:
        # Need to create the full chain: Contents → MediaContentHandles → Media → Comments
        # Use deterministic IDs based on entity_id to avoid duplicates on re-run
        import hashlib, os

        def make_id(suffix: str) -> bytes:
            return hashlib.md5(entity_id + suffix.encode()).digest()

        content_id = make_id("content")
        mch_id = make_id("mch")
        media_id = make_id("media")
        comment_id = make_id("comment")

        cur.execute(
            "INSERT OR REPLACE INTO Contents(Id, Data) VALUES (?, ?)",
            (content_id, aml_data),
        )
        cur.execute(
            "INSERT OR REPLACE INTO MediaContentHandles"
            "(Id, ParentHandleId, Location, LocationType, ContentSize, Compressed, Hash, ContentId)"
            " VALUES (?, ?, ?, 0, ?, 0, '', ?)",
            (mch_id, None, None, len(aml_data), content_id),
        )
        cur.execute(
            "INSERT OR REPLACE INTO Media(Id, CurrentContentHandleId, MediaType, FileExtension)"
            " VALUES (?, ?, 12, 'atext3')",
            (media_id, mch_id),
        )
        cur.execute(
            "INSERT OR REPLACE INTO Comments(Id, MediumId) VALUES (?, ?)",
            (comment_id, media_id),
        )
        cur.execute(
            "UPDATE Entities SET CommentId = ? WHERE Id = ?",
            (comment_id, entity_id),
        )


def update_code_group(
    cur: sqlite3.Cursor,
    tag_id: bytes,
    new_group_name: str,
    group_map: dict[str, bytes],
) -> None:
    """Remove existing group membership and assign to new group (if it exists)."""
    # Remove from all existing groups
    cur.execute("DELETE FROM TagGroupTags WHERE TagId = ?", (tag_id,))

    if new_group_name and new_group_name in group_map:
        group_id = group_map[new_group_name]
        import os
        link_id = os.urandom(16)
        cur.execute(
            "INSERT INTO TagGroupTags(Id, TagGroupId, TagId) VALUES (?, ?, ?)",
            (link_id, group_id, tag_id),
        )


def update_memo_text(
    cur: sqlite3.Cursor,
    memo_id: bytes,
    text: str,
) -> None:
    """Update the AML content for a memo."""
    aml_data = encode_aml(text)
    cur.execute(
        """
        UPDATE Contents SET Data = ?
        WHERE Id = (
            SELECT mch.ContentId
            FROM Memos mo
            JOIN Media m   ON mo.MediumId = m.Id
            JOIN MediaContentHandles mch ON m.CurrentContentHandleId = mch.Id
            WHERE mo.Id = ?
        )
        """,
        (aml_data, memo_id),
    )


def sync_quotation_codes(
    cur: sqlite3.Cursor,
    quot_id: bytes,
    desired_names: list[str],
    name_to_id: dict[str, bytes],
    current_codes: dict[bytes, set[bytes]],
) -> tuple[int, int]:
    """Add/remove code assignments for a quotation. Returns (added, removed)."""
    import os

    desired_ids = {name_to_id[n] for n in desired_names if n in name_to_id}
    current_ids = current_codes.get(quot_id, set())

    to_add = desired_ids - current_ids
    to_remove = current_ids - desired_ids

    for tag_id in to_remove:
        cur.execute(
            "DELETE FROM Links WHERE SourceId = ? AND TargetId = ?",
            (tag_id, quot_id),
        )

    for tag_id in to_add:
        link_id = os.urandom(16)
        # ProjectId: get from first tag
        cur.execute("SELECT ProjectId FROM Tags WHERE Id = ? LIMIT 1", (tag_id,))
        row = cur.fetchone()
        project_id = row[0] if row else ZERO_GUID
        cur.execute(
            "INSERT INTO Links(Id, ProjectId, SourceId, TargetId, RelationTypeId)"
            " VALUES (?, ?, ?, ?, ?)",
            (link_id, project_id, tag_id, quot_id, ZERO_GUID),
        )

    return len(to_add), len(to_remove)


# ── Main command ──────────────────────────────────────────────────────────────


@app.command()
def main(
    db_path: Path = typer.Option(
        None, "--db", help="Path to Atlas.ti SQLite. Auto-detected if not provided."
    ),
    input_dir: Path = typer.Option(
        None, "--in", help="atlas-coding/ directory. Defaults to <workspace>/atlas-coding/."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Parse and report changes without writing to SQLite."
    ),
) -> None:
    """Push atlas-coding/ Markdown edits back into the live Atlas.ti SQLite."""
    check_atlasti_not_running()

    sqlite_path = db_path or find_live_sqlite()
    coding_dir = input_dir or ATLAS_CODING_DIR

    if not coding_dir.exists():
        typer.echo(f"ERROR: {coding_dir} not found. Run atlasti_import.py first.", err=True)
        raise typer.Exit(1)

    codebook_path = coding_dir / "codebook.md"
    memos_path = coding_dir / "memos.md"
    quot_dir = coding_dir / "quotations"

    typer.echo(f"Reading:  {coding_dir}")
    typer.echo(f"Writing:  {sqlite_path}")
    if dry_run:
        typer.echo("Mode:     DRY RUN (no changes will be written)")

    # Parse Markdown
    codes_md = parse_codebook(codebook_path) if codebook_path.exists() else []
    memos_md = parse_memos(memos_path) if memos_path.exists() else []
    quots_md = parse_quotations(quot_dir) if quot_dir.exists() else {}

    typer.echo(
        f"Parsed:   {len(codes_md)} codes, {len(memos_md)} memos, "
        f"{len(quots_md)} quotations from Markdown"
    )

    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = OFF")

    existing_codes = get_existing_codes(cur)
    group_map = get_group_map(cur)
    name_to_id = get_code_name_to_id(cur)
    current_quot_codes = get_quotation_current_codes(cur)

    stats = {
        "names_changed": 0,
        "descriptions_set": 0,
        "groups_changed": 0,
        "memos_updated": 0,
        "quot_codes_added": 0,
        "quot_codes_removed": 0,
        "skipped": 0,
    }
    unknown_groups: set[str] = set()

    # ── Codes ──
    for c in codes_md:
        tag_id = c["id"]
        if tag_id not in existing_codes:
            stats["skipped"] += 1
            continue
        ex = existing_codes[tag_id]

        # Name
        if c["name"] and c["name"] != ex["name"]:
            stats["names_changed"] += 1
            if not dry_run:
                update_entity_name(cur, tag_id, c["name"])

        # Description — only write if non-empty (skip placeholder / untouched codes)
        if c["description"]:
            stats["descriptions_set"] += 1
            if not dry_run:
                upsert_code_description(conn, cur, ex, tag_id, c["description"])

        # Group
        if c["group"] is not None:
            if c["group"] and c["group"] not in group_map:
                unknown_groups.add(c["group"])
            else:
                stats["groups_changed"] += 1
                if not dry_run:
                    update_code_group(cur, tag_id, c["group"], group_map)

    # ── Memos ──
    for m in memos_md:
        if not m["text"]:
            continue
        stats["memos_updated"] += 1
        if not dry_run:
            update_memo_text(cur, m["id"], m["text"])

    # ── Quotation code assignments ──
    for quot_id, desired_names in quots_md.items():
        added, removed = sync_quotation_codes(
            cur, quot_id, desired_names, name_to_id, current_quot_codes
        )
        if not dry_run or True:  # count even in dry-run
            stats["quot_codes_added"] += added
            stats["quot_codes_removed"] += removed

    if not dry_run:
        conn.commit()
    conn.close()

    typer.echo("\nSummary:")
    typer.echo(f"  Code names changed:        {stats['names_changed']}")
    typer.echo(f"  Descriptions set/updated:  {stats['descriptions_set']}")
    typer.echo(f"  Group assignments updated: {stats['groups_changed']}")
    typer.echo(f"  Memos updated:             {stats['memos_updated']}")
    typer.echo(f"  Quotation codes added:     {stats['quot_codes_added']}")
    typer.echo(f"  Quotation codes removed:   {stats['quot_codes_removed']}")

    if unknown_groups:
        typer.echo(
            f"\nWarning: {len(unknown_groups)} group name(s) not found in Atlas.ti "
            f"(skipped): {', '.join(sorted(unknown_groups))}"
        )

    if dry_run:
        typer.echo("\n(Dry run — no changes written to SQLite)")
    else:
        typer.echo("\nDone. Reopen Atlas.ti to see the changes.")


if __name__ == "__main__":
    app()
