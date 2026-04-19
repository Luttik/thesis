#!/usr/bin/env python3
"""atlasti_export.py — Push atlas-coding/ Markdown changes back into the live Atlas.ti SQLite.

Editable elements (written back to Atlas.ti):
  - Code names            (codebook.md  ### headings)
  - Code group membership (codebook.md  **Group**: lines — reassigns to existing groups)
  - Quotation code lists  (quotations/  **Codes**: lines — add/remove codes on existing quotations)
  - New quotations        (documents/   <!-- quote --> annotations)

Read-only in Cursor (edit directly in Atlas.ti):
  - Code descriptions     (AML binary format not yet supported for write-back)
  - Memo text             (AML binary format not yet supported for write-back)

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
    code_quot_rel_type_id: bytes = ZERO_GUID,
    user_id: bytes = ZERO_GUID,
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
        cur.execute("SELECT ProjectId FROM Tags WHERE Id = ? LIMIT 1", (tag_id,))
        row = cur.fetchone()
        project_id = row[0] if row else ZERO_GUID
        cur.execute(
            "INSERT INTO Links(Id, ProjectId, SourceId, TargetId, RelationTypeId)"
            " VALUES (?, ?, ?, ?, ?)",
            (link_id, project_id, tag_id, quot_id, code_quot_rel_type_id),
        )
        # Every Link needs an Entity row or Atlas.ti won't recognise it
        create_entity(cur, link_id, user_id)

    return len(to_add), len(to_remove)


# ── Entity / ChangeLog helpers ───────────────────────────────────────────────

def _get_user_id(cur: sqlite3.Cursor) -> bytes:
    """Return the primary user (OwnerId) for new entities."""
    cur.execute(
        "SELECT OwnerId FROM Entities WHERE OwnerId != ? LIMIT 1",
        (ZERO_GUID,),
    )
    row = cur.fetchone()
    return row[0] if row else ZERO_GUID


def create_entity(
    cur: sqlite3.Cursor,
    obj_id: bytes,
    user_id: bytes,
    name: str | None = None,
) -> None:
    """Create ChangeLogEntries + ChangeLogs + Entities rows for any new Atlas.ti object."""
    import os
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
    entry_id = os.urandom(16)
    changelog_id = os.urandom(16)

    cur.execute(
        "INSERT OR IGNORE INTO ChangeLogEntries"
        "(Id, Timestamp, AuthorId, ChangeLogEntryType, ChangeLogId) VALUES (?,?,?,0,?)",
        (entry_id, now, user_id, changelog_id),
    )
    cur.execute(
        "INSERT OR IGNORE INTO ChangeLogs"
        "(Id, CreationEntryId, LastModificationEntryId) VALUES (?,?,?)",
        (changelog_id, entry_id, ZERO_GUID),
    )
    cur.execute(
        "INSERT OR IGNORE INTO Entities"
        "(Id, Name, OwnerId, ChangeLogId, CommentId, ColorDefinitionId) VALUES (?,?,?,?,?,?)",
        (obj_id, name, user_id, changelog_id, ZERO_GUID, ZERO_GUID),
    )


# ── New quotation creation ────────────────────────────────────────────────────

_QUOTE_BLOCK_RE = re.compile(
    r"<!--\s*quote:\s*(?P<codes>[^-]+?)\s*-->\s*\n(?P<text>.*?)\n<!--\s*/quote\s*-->",
    re.DOTALL,
)
_SEG_LINE_RE = re.compile(r"^<!--\s*seg:(\d+)\s*-->$")
_FALLBACK_WARNING_RE = re.compile(r"Segment numbers will NOT match")


def load_paragraphs_from_doc_md(doc_md: Path) -> tuple[list[str], bool]:
    """Parse a seg-annotated document MD file into an ordered list of paragraphs.

    Returns (paragraphs, is_fallback). Fallback documents have unreliable seg numbers.
    """
    lines = doc_md.read_text(encoding="utf-8").splitlines()
    paragraphs: list[str] = []
    is_fallback = any(_FALLBACK_WARNING_RE.search(ln) for ln in lines)
    current_seg: int | None = None

    for line in lines:
        m = _SEG_LINE_RE.match(line)
        if m:
            seg_idx = int(m.group(1))
            # Ensure list is large enough (fill gaps with empty strings)
            while len(paragraphs) <= seg_idx:
                paragraphs.append("")
            current_seg = seg_idx
        elif current_seg is not None and line.strip() and not line.startswith(">"):
            paragraphs[current_seg] = line.strip()
            current_seg = None

    return paragraphs, is_fallback


def parse_quote_annotations(doc_md: Path) -> list[dict]:
    """Parse <!-- quote: `Code A`, `Code B` --> ... <!-- /quote --> blocks."""
    text = doc_md.read_text(encoding="utf-8")
    annotations = []
    for m in _QUOTE_BLOCK_RE.finditer(text):
        raw_codes = m.group("codes")
        code_names = [c.strip() for c in re.findall(r"`([^`]+)`", raw_codes)]
        quote_text = m.group("text").strip()
        # Strip seg markers that may be inside the quote block
        quote_text = re.sub(r"<!--\s*seg:\d+\s*-->\n?", "", quote_text).strip()
        if code_names and quote_text:
            annotations.append({"codes": code_names, "text": quote_text})
    return annotations


def find_text_in_paragraphs(
    paragraphs: list[str], search_text: str
) -> tuple[int, int, int, int] | None:
    """Locate search_text in the paragraph list.

    Returns (start_seg_0based, start_offset, end_seg_0based, end_offset) or None.
    Offsets are 0-based character positions within the paragraph.
    """
    # Build a flat view joining with \u2029 (single char separator, as Atlas.ti does)
    full = "\u2029".join(paragraphs)
    idx = full.find(search_text)
    if idx == -1:
        return None

    end_idx = idx + len(search_text) - 1

    # Convert flat index to (segment, offset)
    def flat_to_seg_off(flat_idx: int) -> tuple[int, int]:
        cum = 0
        for i, para in enumerate(paragraphs):
            para_end = cum + len(para)
            if flat_idx <= para_end:
                return i, flat_idx - cum
            cum = para_end + 1  # +1 for the \u2029 separator
        return len(paragraphs) - 1, flat_idx - cum

    start_seg, start_off = flat_to_seg_off(idx)
    end_seg, end_off = flat_to_seg_off(end_idx)
    return start_seg, start_off, end_seg, end_off


def compute_intervals(
    paragraphs: list[str],
    start_seg: int,
    start_off: int,
    end_seg: int,
    end_off: int,
) -> tuple[int, int]:
    """Compute Interval_FirstIndex and Interval_LastIndex.

    These are absolute character positions treating the document as paragraphs
    joined by single \u2029 separators.
    """
    cum = 0
    seg_starts: list[int] = []
    for para in paragraphs:
        seg_starts.append(cum)
        cum += len(para) + 1  # +1 for \u2029

    # Atlas.ti's interval_first uses a +1 offset relative to the flat char index
    # (empirically confirmed: all existing quotations show interval_first = cumulative + offset + 1)
    # interval_last uses no such offset.
    first_idx = seg_starts[start_seg] + start_off + 1
    last_idx = seg_starts[end_seg] + end_off
    return first_idx, last_idx


def get_document_map(cur: sqlite3.Cursor) -> dict[str, dict]:
    """Return {doc_name: {id, layer_id, hwm}} for all documents."""
    cur.execute(
        """
        SELECT e.Name, hex(d.Id), d.QuotationHighwaterMark, hex(l.Id), hex(d.MediumId)
        FROM Documents d
        JOIN Entities e ON d.Id = e.Id
        JOIN Layers l ON l.DocumentId = d.Id
        """
    )
    result: dict[str, dict] = {}
    for name, doc_hex, hwm, layer_hex, medium_hex in cur.fetchall():
        if name and name not in result:  # take first layer per doc name
            result[name] = {
                "id": bytes.fromhex(doc_hex),
                "layer_id": bytes.fromhex(layer_hex),
                "hwm": hwm or 0,
                "medium_id": bytes.fromhex(medium_hex),
            }
    return result


def get_project_id(cur: sqlite3.Cursor) -> bytes:
    cur.execute("SELECT Id FROM Projects LIMIT 1")
    row = cur.fetchone()
    return row[0] if row else ZERO_GUID


def get_app_version(cur: sqlite3.Cursor) -> int:
    cur.execute("SELECT AppVersion FROM Locations LIMIT 1")
    row = cur.fetchone()
    return row[0] if row else 419430402  # Atlas.ti 25 default


def get_code_quotation_relation_type_id(cur: sqlite3.Cursor) -> bytes:
    """Return the 'Code->Quotation' RelationTypeId that Atlas.ti requires for all code-quotation links."""
    cur.execute(
        "SELECT r.Id FROM RelationTypes r JOIN Entities e ON r.Id = e.Id WHERE e.Name = 'Code->Quotation'"
    )
    row = cur.fetchone()
    return row[0] if row else ZERO_GUID


def process_new_quotations(
    cur: sqlite3.Cursor,
    doc_dir: Path,
    doc_map: dict[str, dict],
    name_to_id: dict[str, bytes],
    project_id: bytes,
    app_version: int,
    code_quot_rel_type_id: bytes,
    user_id: bytes,
    dry_run: bool,
) -> tuple[int, list[str]]:
    """Process all <!-- quote --> annotations in documents/*.md.

    Returns (quotations_created, error_messages).
    """
    import os

    created = 0
    errors: list[str] = []

    for md_file in sorted(doc_dir.glob("*.md")):
        doc_name_raw = md_file.stem  # e.g. "Thesis transcript Berfun Goodwin"
        annotations = parse_quote_annotations(md_file)
        if not annotations:
            continue

        paragraphs, is_fallback = load_paragraphs_from_doc_md(md_file)
        if is_fallback:
            errors.append(
                f"{md_file.name}: skipping {len(annotations)} annotation(s) — "
                "fallback transcript (segment numbers unreliable)"
            )
            continue

        # Match doc_name_raw to a document in Atlas.ti (strip trailing (hex) suffix)
        clean_name = re.sub(r"\s*\([0-9a-f]{8}\)$", "", doc_name_raw)
        doc_info = doc_map.get(clean_name) or doc_map.get(doc_name_raw)
        if not doc_info:
            errors.append(
                f"{md_file.name}: document not found in Atlas.ti — skipping {len(annotations)} annotation(s)"
            )
            continue

        hwm = doc_info["hwm"]
        layer_id = doc_info["layer_id"]

        for ann in annotations:
            pos = find_text_in_paragraphs(paragraphs, ann["text"])
            if pos is None:
                errors.append(
                    f"{md_file.name}: text not found in document — "
                    f"skipping quote: {ann['text'][:60]!r}"
                )
                continue

            start_seg, start_off, end_seg, end_off = pos
            # Atlas.ti uses 1-based paragraph numbers
            atlas_start_para = start_seg + 1
            atlas_end_para = end_seg + 1

            first_idx, last_idx = compute_intervals(
                paragraphs, start_seg, start_off, end_seg, end_off
            )

            hwm += 1
            location_id = os.urandom(16)
            quot_id = os.urandom(16)

            if not dry_run:
                # Locations row
                cur.execute(
                    "INSERT INTO Locations(Id, AppVersion) VALUES (?, ?)",
                    (location_id, app_version),
                )
                # TextLocations row
                cur.execute(
                    """INSERT INTO TextLocations(
                        Id, StartElementId, StartOffset, EndElementId, EndOffset,
                        StartParagraphNumber, EndParagraphNumber,
                        Interval_FirstIndex, Interval_LastIndex
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        location_id,
                        -2 * atlas_start_para,
                        start_off,
                        -2 * atlas_end_para,
                        end_off,
                        atlas_start_para,
                        atlas_end_para,
                        first_idx,
                        last_idx,
                    ),
                )
                # Quotation row + required Entity/ChangeLog rows
                cur.execute(
                    """INSERT INTO Quotations(Id, Number, PlainText, IsAbbreviated, LayerId, LocationId)
                    VALUES (?, ?, ?, 0, ?, ?)""",
                    (quot_id, hwm, ann["text"], layer_id, location_id),
                )
                create_entity(cur, quot_id, user_id)

                # Link rows (one per code) + required Entity/ChangeLog rows
                for code_name in ann["codes"]:
                    tag_id = name_to_id.get(code_name)
                    if not tag_id:
                        errors.append(
                            f"  Code not found: {code_name!r} — link skipped for this quotation"
                        )
                        continue
                    link_id = os.urandom(16)
                    cur.execute(
                        "INSERT INTO Links(Id, ProjectId, SourceId, TargetId, RelationTypeId)"
                        " VALUES (?, ?, ?, ?, ?)",
                        (link_id, project_id, tag_id, quot_id, code_quot_rel_type_id),
                    )
                    create_entity(cur, link_id, user_id)

            created += 1

        if not dry_run and hwm != doc_info["hwm"]:
            cur.execute(
                "UPDATE Documents SET QuotationHighwaterMark = ? WHERE Id = ?",
                (hwm, doc_info["id"]),
            )
            doc_info["hwm"] = hwm  # update in-memory for subsequent annotations

    return created, errors


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
    doc_dir = coding_dir / "documents"

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
    doc_map = get_document_map(cur)
    project_id = get_project_id(cur)
    app_version = get_app_version(cur)
    code_quot_rel_type_id = get_code_quotation_relation_type_id(cur)
    user_id = _get_user_id(cur)

    stats = {
        "names_changed": 0,
        "groups_changed": 0,
        "quot_codes_added": 0,
        "quot_codes_removed": 0,
        "new_quotations": 0,
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

        # Description — AML binary write-back is not yet supported (format not fully
        # reverse-engineered; writing crashes Atlas.ti). Descriptions in codebook.md
        # are read-only context for the agent; set them manually in Atlas.ti.
        # if c["description"]:
        #     upsert_code_description(conn, cur, ex, tag_id, c["description"])

        # Group
        if c["group"] is not None:
            if c["group"] and c["group"] not in group_map:
                unknown_groups.add(c["group"])
            else:
                stats["groups_changed"] += 1
                if not dry_run:
                    update_code_group(cur, tag_id, c["group"], group_map)

    # ── Memos ──
    # AML binary write-back is not yet supported for memo text.
    # Memos in memos.md are read context only; edit memo text directly in Atlas.ti.

    # ── Quotation code assignments (existing quotations) ──
    for quot_id, desired_names in quots_md.items():
        added, removed = sync_quotation_codes(
            cur, quot_id, desired_names, name_to_id, current_quot_codes,
            code_quot_rel_type_id, user_id
        )
        if not dry_run or True:  # count even in dry-run
            stats["quot_codes_added"] += added
            stats["quot_codes_removed"] += removed

    # ── New quotations from <!-- quote --> annotations in documents/ ──
    new_quot_errors: list[str] = []
    if doc_dir.exists():
        n_created, new_quot_errors = process_new_quotations(
            cur, doc_dir, doc_map, name_to_id, project_id, app_version,
            code_quot_rel_type_id, user_id, dry_run
        )
        stats["new_quotations"] = n_created

    if not dry_run:
        conn.commit()
    conn.close()

    typer.echo("\nSummary:")
    typer.echo(f"  Code names changed:        {stats['names_changed']}")
    typer.echo(f"  Group assignments updated: {stats['groups_changed']}")
    typer.echo(f"  Quotation codes added:     {stats['quot_codes_added']}")
    typer.echo(f"  Quotation codes removed:   {stats['quot_codes_removed']}")
    typer.echo(f"  New quotations created:    {stats['new_quotations']}")
    typer.echo("  (Descriptions and memo text: edit directly in Atlas.ti)")

    if unknown_groups:
        typer.echo(
            f"\nWarning: {len(unknown_groups)} group name(s) not found in Atlas.ti "
            f"(skipped): {', '.join(sorted(unknown_groups))}"
        )

    if new_quot_errors:
        typer.echo(f"\nNew quotation warnings ({len(new_quot_errors)}):")
        for e in new_quot_errors:
            typer.echo(f"  - {e}")

    if dry_run:
        typer.echo("\n(Dry run — no changes written to SQLite)")
    else:
        typer.echo("\nDone. Reopen Atlas.ti to see the changes.")


if __name__ == "__main__":
    app()
