#!/usr/bin/env python3
"""Apply deterministic quotation operations to an Atlas.ti SQLite project.

This script avoids fuzzy Markdown parsing by using explicit quote operations
stored in JSON. It supports paragraph-level and sub-paragraph quotations.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path


ZERO_GUID = b"\x00" * 16
LIB_SUFFIX = Path("AppData") / "Roaming" / "Scientific Software" / "ATLASti.25" / "Libraries25"


def _normalize_host_path(path: Path | str) -> Path:
    s = str(path)
    if os.name != "nt" and re.match(r"^[A-Za-z]:[\\/]", s):
        drive = s[0].lower()
        rest = s[2:].replace("\\", "/").lstrip("/")
        return Path("/mnt") / drive / rest
    return Path(path)


def find_live_sqlite() -> Path:
    candidates = [Path.home() / LIB_SUFFIX]
    users_root = Path("/mnt/c/Users")
    if users_root.exists():
        for user_dir in users_root.iterdir():
            candidates.append(user_dir / LIB_SUFFIX)
    seen: set[str] = set()
    for base in candidates:
        k = str(base)
        if k in seen or not base.exists():
            continue
        seen.add(k)
        for lib_dir in base.iterdir():
            if not lib_dir.is_dir() or lib_dir.name == "Local":
                continue
            for f in lib_dir.glob("*.sqlite"):
                if "_B_" not in f.name and "_WC_" not in f.name:
                    return f
    raise FileNotFoundError("No live Atlas.ti SQLite found.")


def contents_dir_from_db(db_path: Path) -> Path:
    p = _normalize_host_path(db_path)
    for parent in [p.parent, *p.parents]:
        if parent.name == "Libraries25":
            return parent / "Local" / "Contents"
    raise ValueError(f"Cannot infer Libraries25 from DB path: {db_path}")


def decode_aml_paragraphs(path: Path) -> list[str]:
    data = path.read_bytes()
    if len(data) < 24:
        return []
    text_start = struct.unpack_from("<q", data, 16)[0]
    raw = data[text_start:].decode("utf-16-le", errors="ignore")
    raw = raw[8:]
    raw = re.sub(r"^[^\x20-\x7e\u2029\r\n]*", "", raw)
    raw = re.sub(r"[\ufffe\uffff].*$", "", raw, flags=re.DOTALL)
    raw = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", raw)
    raw = re.sub(r"  +", " ", raw)
    # Keep exact paragraph contents for offset math.
    # Trimming introduces systematic drift between calculated offsets and
    # Atlas.ti TextLocation offsets.
    return raw.split("\u2029")


def get_owner_id(cur: sqlite3.Cursor) -> bytes:
    cur.execute("SELECT OwnerId FROM Entities WHERE OwnerId != ? LIMIT 1", (ZERO_GUID,))
    row = cur.fetchone()
    return row[0] if row else ZERO_GUID


def create_entity(cur: sqlite3.Cursor, obj_id: bytes, owner_id: bytes, name: str | None = None) -> None:
    import os as _os
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
    entry_id = _os.urandom(16)
    changelog_id = _os.urandom(16)
    cur.execute(
        "INSERT OR IGNORE INTO ChangeLogEntries(Id, Timestamp, AuthorId, ChangeLogEntryType, ChangeLogId) VALUES (?,?,?,0,?)",
        (entry_id, now, owner_id, changelog_id),
    )
    cur.execute(
        "INSERT OR IGNORE INTO ChangeLogs(Id, CreationEntryId, LastModificationEntryId) VALUES (?,?,?)",
        (changelog_id, entry_id, ZERO_GUID),
    )
    cur.execute(
        "INSERT OR IGNORE INTO Entities(Id, Name, OwnerId, ChangeLogId, CommentId, ColorDefinitionId) VALUES (?,?,?,?,?,?)",
        (obj_id, name, owner_id, changelog_id, ZERO_GUID, ZERO_GUID),
    )


@dataclass
class QuoteOp:
    doc_id: bytes
    paragraph: int  # zero-based
    codes: list[str]
    text: str | None = None
    start: int | None = None
    end: int | None = None  # exclusive


def parse_ops(path: Path) -> list[QuoteOp]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    ops: list[QuoteOp] = []
    for item in payload.get("operations", []):
        ops.append(
            QuoteOp(
                doc_id=bytes.fromhex(item["doc_id"]),
                paragraph=int(item["paragraph"]),
                codes=list(item["codes"]),
                text=item.get("text"),
                start=item.get("start"),
                end=item.get("end"),
            )
        )
    return ops


def main() -> None:
    import argparse
    import os as _os

    ap = argparse.ArgumentParser(description="Apply deterministic quote operations to Atlas.ti DB")
    ap.add_argument("--db", type=Path, default=None)
    ap.add_argument("--ops", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    db_path = _normalize_host_path(args.db) if args.db else find_live_sqlite()
    ops = parse_ops(args.ops)
    contents_dir = contents_dir_from_db(db_path)

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys = OFF")

    owner_id = get_owner_id(cur)
    cur.execute("SELECT Id FROM Projects LIMIT 1")
    project_id = cur.fetchone()[0]
    cur.execute("SELECT AppVersion FROM Locations LIMIT 1")
    app_version = cur.fetchone()[0]
    cur.execute("SELECT r.Id FROM RelationTypes r JOIN Entities e ON r.Id=e.Id WHERE e.Name='Code->Quotation'")
    rel_type_id = cur.fetchone()[0]
    cur.execute("SELECT e.Name, t.Id FROM Tags t JOIN Entities e ON t.Id=e.Id WHERE t.TagType=0")
    code_map = {name: tid for name, tid in cur.fetchall()}

    cur.execute(
        """
        SELECT d.Id, e.Name, l.Id, d.QuotationHighwaterMark, mch.Location
        FROM Documents d
        JOIN Entities e ON d.Id = e.Id
        JOIN Layers l ON l.DocumentId = d.Id
        LEFT JOIN Media m ON d.MediumId = m.Id
        LEFT JOIN MediaContentHandles mch ON m.CurrentContentHandleId = mch.Id
        WHERE hex(d.ProjectId) != '00000000000000000000000000000000'
        """
    )
    doc_map = {row[0]: {"name": row[1], "layer_id": row[2], "hwm": row[3] or 0, "location": row[4] or ""} for row in cur.fetchall()}

    created = 0
    linked = 0
    errors: list[str] = []

    for op in ops:
        doc = doc_map.get(op.doc_id)
        if not doc:
            errors.append(f"doc_id not found: {op.doc_id.hex().upper()}")
            continue
        aml_path = contents_dir / doc["location"]
        if not aml_path.exists():
            errors.append(f"content not found for {doc['name']}: {aml_path}")
            continue
        paras = decode_aml_paragraphs(aml_path)
        if op.paragraph < 0 or op.paragraph >= len(paras):
            errors.append(f"paragraph out of range for {doc['name']}: {op.paragraph}")
            continue
        para = paras[op.paragraph]

        if op.start is None or op.end is None:
            if op.text is None:
                start = 0
                end = len(para)
            else:
                idx = para.find(op.text)
                if idx < 0:
                    errors.append(f"text not found in paragraph {op.paragraph} for {doc['name']}")
                    continue
                if para.find(op.text, idx + 1) != -1:
                    errors.append(f"text appears multiple times in paragraph {op.paragraph} for {doc['name']}")
                    continue
                start = idx
                end = idx + len(op.text)
        else:
            start = int(op.start)
            end = int(op.end)

        if start < 0 or end <= start or end > len(para):
            errors.append(f"invalid offsets for {doc['name']} paragraph {op.paragraph}: {start}-{end}")
            continue

        cum = 0
        for p in paras[: op.paragraph]:
            cum += len(p) + 1
        first_idx = cum + start
        last_idx = cum + end - 1
        atlas_para = op.paragraph + 1
        text = para[start:end]

        cur.execute(
            """
            SELECT q.Id
            FROM Quotations q
            JOIN TextLocations tl ON q.LocationId = tl.Id
            WHERE q.LayerId = ? AND tl.StartParagraphNumber = ?
              AND tl.StartOffset = ? AND tl.EndParagraphNumber = ? AND tl.EndOffset = ?
            LIMIT 1
            """,
            (doc["layer_id"], atlas_para, start, atlas_para, end),
        )
        row = cur.fetchone()
        if row:
            quot_id = row[0]
        else:
            location_id = _os.urandom(16)
            quot_id = _os.urandom(16)
            if not args.dry_run:
                cur.execute("INSERT INTO Locations(Id, AppVersion) VALUES (?, ?)", (location_id, app_version))
                cur.execute(
                    """
                    INSERT INTO TextLocations(
                        Id, StartElementId, StartOffset, EndElementId, EndOffset,
                        StartParagraphNumber, EndParagraphNumber, Interval_FirstIndex, Interval_LastIndex
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (location_id, -2 * atlas_para, start, -2 * atlas_para, end, atlas_para, atlas_para, first_idx, last_idx),
                )
                doc["hwm"] += 1
                cur.execute(
                    "INSERT INTO Quotations(Id, Number, PlainText, IsAbbreviated, LayerId, LocationId) VALUES (?, ?, ?, ?, ?, ?)",
                    (quot_id, doc["hwm"], text, 1 if (start > 0 or end < len(para)) else 0, doc["layer_id"], location_id),
                )
                create_entity(cur, quot_id, owner_id)
            created += 1

        cur.execute("SELECT SourceId FROM Links WHERE TargetId = ?", (quot_id,))
        existing_links = {r[0] for r in cur.fetchall()}
        for cname in op.codes:
            code_id = code_map.get(cname)
            if not code_id:
                errors.append(f"code not found: {cname}")
                continue
            if code_id in existing_links:
                continue
            if not args.dry_run:
                link_id = _os.urandom(16)
                cur.execute(
                    "INSERT INTO Links(Id, ProjectId, SourceId, TargetId, RelationTypeId) VALUES (?, ?, ?, ?, ?)",
                    (link_id, project_id, code_id, quot_id, rel_type_id),
                )
                create_entity(cur, link_id, owner_id)
            linked += 1

        if not args.dry_run:
            cur.execute("UPDATE Documents SET QuotationHighwaterMark = ? WHERE Id = ?", (doc["hwm"], op.doc_id))

    if not args.dry_run:
        con.commit()
    con.close()

    print(f"created quotations: {created}")
    print(f"added code links: {linked}")
    if errors:
        print(f"errors: {len(errors)}")
        for e in errors:
            print(f"- {e}")


if __name__ == "__main__":
    main()
