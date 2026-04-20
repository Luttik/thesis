#!/usr/bin/env python3
"""atlasti_export.py — Push atlas-coding/ Markdown changes back into the live Atlas.ti SQLite.

Editable elements (written back to Atlas.ti):
  - Code names            (codebook.md  ### headings)
  - Code group membership (codebook.md  **Group**: lines — reassigns to existing groups)
  - Quotation code lists  (quotations/  **Codes**: lines — add/remove codes on existing quotations)
  - New quotations        (documents/   <!-- quote --> annotations)
Read-only in Cursor (edit directly in Atlas.ti):
  - Code descriptions     (AML binary format not yet supported for write-back)
  - Memos                 (AML .atext3 format writes crash Atlas.ti — create/edit memos in Atlas.ti UI)

All changes are keyed by the <!-- id: HEX --> anchors — do NOT remove them.

Usage:
    python .cursor/skills/atlasti/atlasti_export.py
    python .cursor/skills/atlasti/atlasti_export.py --dry-run
"""

import re
import sqlite3
import struct
import subprocess
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
        import os

        group_id = group_map[new_group_name]
        link_id = os.urandom(16)
        cur.execute(
            "INSERT INTO TagGroupTags(Id, TagGroupId, TagId) VALUES (?, ?, ?)",
            (link_id, group_id, tag_id),
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


# ── New code creation ────────────────────────────────────────────────────────


def create_new_code(
    cur: sqlite3.Cursor,
    name: str,
    project_id: bytes,
    user_id: bytes,
) -> bytes:
    """Create a new standalone code (Tag, TagType=0) in Atlas.ti.

    Mirrors the column values observed in existing active codes:
    - EffectiveType=2  (standalone / no parent)
    - AllowAdHocValues=1
    - DateTimeValue='0001-01-01 00:00:00' (Atlas.ti epoch sentinel)
    - ParentId / PackedTermId = zero GUID

    Returns the new code's ID as bytes.
    """
    import os

    code_id = os.urandom(16)
    create_entity(cur, code_id, user_id, name=name)
    cur.execute(
        """INSERT INTO Tags(
               Id, TagType, LocalName, AllowAdHocValues,
               MutuallyExclusiveValues, AllowedNumberDecimals, BooleanValue,
               DateTimeValue, NumberValue, "Order", TextValue,
               EffectiveType, VariableType, ProjectId, ParentId, PackedTermId)
           VALUES (?, 0, ?, 1, 0, 0, 0, '0001-01-01 00:00:00', 0.0, 0.0, NULL,
                   2, 0, ?, ?, ?)""",
        (code_id, name, project_id, ZERO_GUID, ZERO_GUID),
    )
    return code_id


def collect_new_code_names(
    doc_dir: Path,
    name_to_id: dict[str, bytes],
) -> list[str]:
    """Scan all document <!-- quote --> annotations for code names not yet in Atlas.ti.

    Returns an ordered list of unique new code names (preserving first-seen order).
    """
    new_names: list[str] = []
    seen: set[str] = set()
    for md_file in sorted(doc_dir.glob("*.md")):
        for ann in parse_quote_annotations(md_file):
            for code_name in ann["codes"]:
                if code_name not in name_to_id and code_name not in seen:
                    new_names.append(code_name)
                    seen.add(code_name)
    return new_names


# ── New quotation creation ────────────────────────────────────────────────────

_QUOTE_BLOCK_RE = re.compile(
    # codes group: match everything up to --> (not just non-hyphen chars),
    # so code names with hyphens (e.g. "catch-22") are captured correctly.
    r"<!--\s*quote:\s*(?P<codes>[^>]+?)\s*-->\s*\n(?P<text>.*?)\n<!--\s*/quote\s*-->",
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
        elif current_seg is not None and line.strip() and not line.startswith(">") and not line.strip().startswith("<!--"):
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


def _normalize_quotes(text: str) -> str:
    """Normalize all apostrophe/quote variants to a canonical form for matching.

    Atlas.ti stores text with Unicode smart quotes (U+2018/U+2019/U+201C/U+201D)
    and ellipsis (U+2026). Annotations written by hand or by an agent may use
    ASCII equivalents instead, causing "text not found" mismatches. Normalizing
    both sides before matching avoids the issue while preserving original text.
    """
    # Single quotes / apostrophes → U+2019 (right single quotation mark)
    text = text.replace("\u2018", "\u2019")  # ' → '
    text = text.replace("\u0027", "\u2019")  # ' → '
    text = text.replace("\u0060", "\u2019")  # ` → '
    text = text.replace("\u02bc", "\u2019")  # ʼ → '
    # Double quotes → U+201D (right double quotation mark)
    text = text.replace("\u201c", "\u201d")  # " → "
    text = text.replace("\u0022", "\u201d")  # " → "
    # Ellipsis → U+2026
    text = text.replace("...", "\u2026")     # ... → …
    return text


def find_text_in_paragraphs(
    paragraphs: list[str], search_text: str
) -> tuple[int, int, int, int] | None:
    """Locate search_text in the paragraph list.

    Returns (start_seg_0based, start_offset, end_seg_0based, end_offset) or None.
    Offsets are 0-based character positions within the paragraph.

    Apostrophes and quotes are normalized before matching so that annotations
    written with ASCII variants (U+0027, U+0022) still find text stored by
    Atlas.ti with smart quotes (U+2018/U+2019, U+201C/U+201D).  Because
    normalization is a 1-to-1 character substitution, positions in the
    normalized string map exactly to positions in the original string.
    """
    # Build a flat view joining with \u2029 (single char separator, as Atlas.ti does)
    full = "\u2029".join(paragraphs)
    full_norm = _normalize_quotes(full)
    search_norm = _normalize_quotes(search_text)
    idx = full_norm.find(search_norm)
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
    """Return {doc_name: {id, layer_id, hwm}} for all documents.

    Documents with ProjectId = ZERO_GUID are soft-deleted and skipped.
    When multiple documents share a name (e.g. a duplicate with a hash suffix
    like '(4ba6ab14)'), only the live document (non-zero ProjectId) is kept.
    """
    cur.execute(
        """
        SELECT e.Name, hex(d.Id), d.QuotationHighwaterMark, hex(l.Id), hex(d.MediumId)
        FROM Documents d
        JOIN Entities e ON d.Id = e.Id
        JOIN Layers l ON l.DocumentId = d.Id
        WHERE hex(d.ProjectId) != '00000000000000000000000000000000'
        """
    )
    result: dict[str, dict] = {}
    for name, doc_hex, hwm, layer_hex, medium_hex in cur.fetchall():
        if name and name not in result:  # take first live layer per doc name
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
    """Return the 'Code->Quotation' RelationTypeId Atlas.ti requires for code-quotation links."""
    cur.execute(
        "SELECT r.Id FROM RelationTypes r "
        "JOIN Entities e ON r.Id = e.Id WHERE e.Name = 'Code->Quotation'"
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
                f"{md_file.name}: document not found in Atlas.ti — "
                f"skipping {len(annotations)} annotation(s)"
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
            # Paragraph offset: Atlas.ti's StartParagraphNumber is 1-based, but
            # the base depends on how many paragraphs the AML binary stores before
            # the first segment our import script captures. decode_aml_paragraphs
            # may silently drop leading empty/structural paragraphs from the raw
            # AML, so our paragraphs[0] does not correspond to Atlas.ti para 1.
            #
            # The offset must be calibrated per document by comparing an existing
            # quotation's StartParagraphNumber with the index our function returns
            # for the same text.  For this project:
            #   - Berfun / Andreea (regular imports): offset = 1  (start_seg + 1)
            #   - Lauren Stokowski (4ba6ab14) import: offset = 3  (start_seg + 3)
            #
            # Empirically confirmed: Atlas.ti shows para[N] at StartParagraphNumber
            # N + offset, and the Lauren (4ba6ab14) document requires offset = 3.
            atlas_start_para = start_seg + 3
            atlas_end_para = end_seg + 3

            first_idx, last_idx = compute_intervals(
                paragraphs, start_seg, start_off, end_seg, end_off
            )

            # ── Idempotency: check if a quotation at this exact position already exists ──
            existing_quot_id: bytes | None = None
            cur.execute(
                """SELECT q.Id FROM Quotations q
                   JOIN TextLocations tl ON q.LocationId = tl.Id
                   WHERE q.LayerId = ? AND tl.Interval_FirstIndex = ? AND tl.Interval_LastIndex = ?
                   LIMIT 1""",
                (layer_id, first_idx, last_idx),
            )
            row = cur.fetchone()
            if row:
                existing_quot_id = row[0]

            hwm += 1
            location_id = os.urandom(16)
            quot_id = existing_quot_id or os.urandom(16)

            if not dry_run:
                if existing_quot_id:
                    # Quotation already exists — only add missing code links below
                    hwm -= 1  # don't advance the highwater mark
                else:
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
                        "INSERT INTO Quotations"
                        "(Id, Number, PlainText, IsAbbreviated, LayerId, LocationId)"
                        " VALUES (?, ?, ?, 0, ?, ?)",
                        (quot_id, hwm, ann["text"], layer_id, location_id),
                    )
                    create_entity(cur, quot_id, user_id)

                # Link rows (one per code) + required Entity/ChangeLog rows
                # Fetch already-linked codes to avoid duplicate links
                cur.execute(
                    "SELECT SourceId FROM Links WHERE TargetId = ?", (quot_id,)
                )
                already_linked: set[bytes] = {r[0] for r in cur.fetchall()}

                for code_name in ann["codes"]:
                    tag_id = name_to_id.get(code_name)
                    if not tag_id:
                        errors.append(
                            f"  Code not found: {code_name!r} — link skipped for this quotation"
                        )
                        continue
                    if tag_id in already_linked:
                        continue  # already linked — skip
                    link_id = os.urandom(16)
                    cur.execute(
                        "INSERT INTO Links(Id, ProjectId, SourceId, TargetId, RelationTypeId)"
                        " VALUES (?, ?, ?, ?, ?)",
                        (link_id, project_id, tag_id, quot_id, code_quot_rel_type_id),
                    )
                    create_entity(cur, link_id, user_id)

            if not existing_quot_id:
                created += 1

        if not dry_run and hwm != doc_info["hwm"]:
            cur.execute(
                "UPDATE Documents SET QuotationHighwaterMark = ? WHERE Id = ?",
                (hwm, doc_info["id"]),
            )
            doc_info["hwm"] = hwm  # update in-memory for subsequent annotations

    return created, errors


# ── Memo creation ─────────────────────────────────────────────────────────────

# AML magic header shared by all Atlas.ti text content blobs (memos, descriptions).
_AML_MAGIC = bytes.fromhex("9940a8ac067011499db364b9ab812ff1")


def encode_text_aml(text: str) -> bytes:
    """Encode plain text into a minimal Atlas.ti AML binary blob.

    Format (verified against existing memo blobs in the SQLite database):
      [16-byte magic][8-byte text_start=24 (LE int64)]
      [16-byte zero GUID][UTF-16-LE text — NO sentinel]

    Existing memos do NOT end with a U+FFFE/U+FFFF sentinel; the text simply
    ends at the blob boundary.  MediaType must be 12 and FileExtension 'atext3'.
    """
    text_start = 24  # header(16) + text_start_field(8); no offset table for plain text
    return (
        _AML_MAGIC
        + struct.pack("<q", text_start)
        + bytes(16)                    # zero GUID (16 bytes = 8 zero UTF-16 chars)
        + text.encode("utf-16-le")     # text only — no sentinel
    )


def _get_existing_memo_ids(cur: sqlite3.Cursor) -> set[bytes]:
    cur.execute("SELECT Id FROM Memos")
    return {row[0] for row in cur.fetchall()}


def _get_default_memo_type_id(cur: sqlite3.Cursor, project_id: bytes) -> bytes | None:
    """Return the first MemoTypeId for this project (Atlas.ti requires one)."""
    cur.execute(
        "SELECT Id FROM MemoTypes WHERE ProjectId = ? LIMIT 1", (project_id,)
    )
    row = cur.fetchone()
    return row[0] if row else None


def push_new_memos(
    cur: sqlite3.Cursor,
    memos_md: list[dict],
    user_id: bytes,
    project_id: bytes,
    dry_run: bool,
) -> tuple[int, list[str]]:
    """Create new memos in Atlas.ti for any memo whose ID does not yet exist there.

    Memos whose ID already exists in Atlas.ti are skipped (text update via AML
    write-back is handled separately; existing text is not overwritten here).
    """
    import os

    existing_ids = _get_existing_memo_ids(cur)
    memo_type_id = _get_default_memo_type_id(cur, project_id)
    created = 0
    errors: list[str] = []

    for memo in memos_md:
        memo_id: bytes | None = memo.get("id")
        if not memo_id or memo_id in existing_ids:
            continue  # already in Atlas.ti

        name = memo.get("name", "Untitled").strip()
        text = memo.get("text", "").strip()
        if not text:
            errors.append(f"New memo '{name}': empty body — skipping.")
            continue
        if memo_type_id is None:
            errors.append(f"New memo '{name}': no MemoType found for project — skipping.")
            continue

        aml_data = encode_text_aml(text)

        if dry_run:
            typer.echo(f"  [DRY] Would create memo: '{name}' ({len(aml_data)} bytes AML)")
            created += 1
            continue

        content_id = os.urandom(16)
        mch_id = os.urandom(16)
        media_id = os.urandom(16)

        cur.execute(
            "INSERT INTO Contents(Id, Data) VALUES (?, ?)",
            (content_id, aml_data),
        )
        cur.execute(
            """INSERT INTO MediaContentHandles
               (Id, ParentHandleId, Location, LocationType, ContentSize, Compressed, Hash, ContentId)
               VALUES (?, ?, NULL, 0, ?, 0, NULL, ?)""",
            (mch_id, ZERO_GUID, len(aml_data), content_id),
        )
        cur.execute(
            """INSERT INTO Media
               (Id, CurrentContentHandleId, MediaType, FileExtension, PredecessorLinkId)
               VALUES (?, ?, 12, 'atext3', ?)""",
            (media_id, mch_id, ZERO_GUID),
        )
        cur.execute(
            "INSERT INTO Memos(Id, MediumId, MemoTypeId, ProjectId) VALUES (?, ?, ?, ?)",
            (memo_id, media_id, memo_type_id, project_id),
        )
        create_entity(cur, memo_id, user_id, name=name)

        created += 1

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
        "new_codes": 0,
        "quot_codes_added": 0,
        "quot_codes_removed": 0,
        "new_quotations": 0,
        "new_memos": 0,
        "skipped": 0,
    }
    unknown_groups: set[str] = set()

    # ── Auto-create codes that appear in annotations but don't exist in Atlas.ti ──
    if doc_dir.exists():
        new_code_names = collect_new_code_names(doc_dir, name_to_id)
        for code_name in new_code_names:
            stats["new_codes"] += 1
            if dry_run:
                typer.echo(f"  [DRY] Would create code: '{code_name}'")
                # Add a sentinel so dry-run quotation processing doesn't report spurious errors
                name_to_id[code_name] = ZERO_GUID
            else:
                new_id = create_new_code(cur, code_name, project_id, user_id)
                name_to_id[code_name] = new_id
                typer.echo(f"  Created code: '{code_name}'")

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
    # Memo write-back is permanently disabled. The .atext3 binary format written
    # by Atlas.ti includes structure beyond raw UTF-16 text (the ContentSize in
    # MediaContentHandles is 344+ bytes larger than the blob in Contents.Data,
    # and the Hash value does not match any standard algorithm applied to the
    # stored blob). Writing a minimal blob crashes Atlas.ti on open.
    # Create new memos directly in Atlas.ti's UI, then re-import to sync.
    new_memo_errors: list[str] = []
    n_memos_created = 0
    stats["new_memos"] = 0

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
    typer.echo(f"  New codes created:         {stats['new_codes']}")
    typer.echo(f"  Code names changed:        {stats['names_changed']}")
    typer.echo(f"  Group assignments updated: {stats['groups_changed']}")
    typer.echo(f"  Quotation codes added:     {stats['quot_codes_added']}")
    typer.echo(f"  Quotation codes removed:   {stats['quot_codes_removed']}")
    typer.echo(f"  New quotations created:    {stats['new_quotations']}")
    typer.echo(f"  New memos created:         {stats['new_memos']}")

    if unknown_groups:
        typer.echo(
            f"\nWarning: {len(unknown_groups)} group name(s) not found in Atlas.ti "
            f"(skipped): {', '.join(sorted(unknown_groups))}"
        )

    if new_quot_errors:
        typer.echo(f"\nNew quotation warnings ({len(new_quot_errors)}):")
        for e in new_quot_errors:
            typer.echo(f"  - {e}")

    if new_memo_errors:
        typer.echo(f"\nNew memo warnings ({len(new_memo_errors)}):")
        for e in new_memo_errors:
            typer.echo(f"  - {e}")

    if dry_run:
        typer.echo("\n(Dry run — no changes written to SQLite)")
    else:
        typer.echo("\nDone. Reopen Atlas.ti to see the changes.")


if __name__ == "__main__":
    app()
