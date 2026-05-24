#!/usr/bin/env python3
"""Verify that quote operations were applied exactly as requested.

Checks for each operation:
- Target document exists
- Quotation exists at expected paragraph/offset
- Quotation text matches expected text (for text-based ops)
- All expected code links are present

Exit code is non-zero when any check fails.
"""

from __future__ import annotations

import argparse
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
    return raw.split("\u2029")


@dataclass
class QuoteOp:
    doc_id: bytes
    paragraph: int
    codes: list[str]
    text: str | None = None
    start: int | None = None
    end: int | None = None


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
    ap = argparse.ArgumentParser(description="Verify Atlas quote operations were applied correctly")
    ap.add_argument("--ops", type=Path, required=True)
    ap.add_argument("--db", type=Path, default=None)
    args = ap.parse_args()

    db_path = _normalize_host_path(args.db) if args.db else find_live_sqlite()
    ops = parse_ops(args.ops)
    contents_dir = contents_dir_from_db(db_path)

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute(
        """
        SELECT d.Id, e.Name, l.Id, mch.Location
        FROM Documents d
        JOIN Entities e ON d.Id = e.Id
        JOIN Layers l ON l.DocumentId = d.Id
        LEFT JOIN Media m ON d.MediumId = m.Id
        LEFT JOIN MediaContentHandles mch ON m.CurrentContentHandleId = mch.Id
        WHERE hex(d.ProjectId) != '00000000000000000000000000000000'
        """
    )
    doc_map = {row[0]: {"name": row[1], "layer_id": row[2], "location": row[3] or ""} for row in cur.fetchall()}

    cur.execute("SELECT e.Name, t.Id FROM Tags t JOIN Entities e ON t.Id=e.Id WHERE t.TagType=0")
    code_map = {name: tid for name, tid in cur.fetchall()}

    verified = 0
    errors: list[str] = []

    for idx, op in enumerate(ops, start=1):
        doc = doc_map.get(op.doc_id)
        if not doc:
            errors.append(f"#{idx}: doc not found: {op.doc_id.hex().upper()}")
            continue

        aml_path = contents_dir / doc["location"]
        if not aml_path.exists():
            errors.append(f"#{idx}: content file missing for {doc['name']}")
            continue

        paras = decode_aml_paragraphs(aml_path)
        if op.paragraph < 0 or op.paragraph >= len(paras):
            errors.append(f"#{idx}: paragraph out of range for {doc['name']}: {op.paragraph}")
            continue
        para = paras[op.paragraph]

        if op.start is None or op.end is None:
            if op.text is None:
                start = 0
                end = len(para)
            else:
                first = para.find(op.text)
                if first < 0:
                    errors.append(f"#{idx}: text not found in paragraph {op.paragraph}")
                    continue
                again = para.find(op.text, first + 1)
                if again != -1:
                    errors.append(f"#{idx}: text is not unique in paragraph {op.paragraph}")
                    continue
                start = first
                end = first + len(op.text)
        else:
            start = int(op.start)
            end = int(op.end)

        atlas_para = op.paragraph + 1

        cur.execute(
            """
            SELECT q.Id, q.PlainText
            FROM Quotations q
            JOIN TextLocations tl ON q.LocationId = tl.Id
            WHERE q.LayerId = ? AND tl.StartParagraphNumber = ?
              AND tl.StartOffset = ? AND tl.EndParagraphNumber = ? AND tl.EndOffset = ?
            LIMIT 1
            """,
            (doc["layer_id"], atlas_para, start, atlas_para, end),
        )
        row = cur.fetchone()
        if not row:
            errors.append(f"#{idx}: quotation not found at expected position (para {op.paragraph}, {start}-{end})")
            continue

        qid, plain_text = row
        if op.text is not None and plain_text != op.text:
            errors.append(f"#{idx}: quotation text mismatch for para {op.paragraph}")
            continue

        cur.execute("SELECT SourceId FROM Links WHERE TargetId = ?", (qid,))
        linked = {r[0] for r in cur.fetchall()}
        missing_codes = [c for c in op.codes if code_map.get(c) not in linked]
        if missing_codes:
            errors.append(f"#{idx}: missing code links: {', '.join(missing_codes)}")
            continue

        verified += 1

    con.close()

    print(f"verified operations: {verified}/{len(ops)}")
    if errors:
        print(f"errors: {len(errors)}")
        for e in errors:
            print(f"- {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
