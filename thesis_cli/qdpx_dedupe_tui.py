#!/usr/bin/env python3
"""Review likely duplicate QDPX codes in a terminal UI.

This tool parses a QDPX archive, embeds code semantics locally, computes
pairwise cosine similarity, and opens a binary-review TUI:

- `a`: dedupe and keep name of code A
- `b`: dedupe and keep name of code B
- `c`: dedupe with a custom merged name
- `s`: keep separate
- `j`/`k`: next/previous candidate
- `z`: undo

State is autosaved and can be resumed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast
from xml.etree import ElementTree as ET

import numpy as np
from rich.console import Console
from rich.markup import escape
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Input, Static

from thesis_cli.qdpx_dedupe_apply import apply_decisions_to_qdpx

QDA_NS = "urn:QDA-XML:project:1.0"
NS = {"q": QDA_NS}

DEFAULT_MODEL = "BAAI/bge-m3"
DEFAULT_STATE_PATH = Path("output/qdpx-dedupe-review.json")
DEFAULT_CANDIDATES_CSV = Path("output/qdpx-dedupe-candidates.csv")
DEFAULT_REVIEW_CSV = Path("output/qdpx-dedupe-review.csv")
DEFAULT_REVIEW_MD = Path("output/qdpx-dedupe-review.md")
DEFAULT_CACHE_DIR = Path(".cache/qdpx-dedupe")
DEFAULT_LOOKUP_DB = "embedding_lookup.sqlite"
CONSOLE = Console()


@dataclass
class QuoteSnippet:
    source_name: str
    text: str


@dataclass
class CodeRecord:
    guid: str
    name: str
    full_name: str
    description: str
    parent_guid: str | None
    quotes: list[QuoteSnippet] = field(default_factory=list)

    @property
    def usage_count(self) -> int:
        return len(self.quotes)


@dataclass
class Candidate:
    guid_a: str
    guid_b: str
    code_a: str
    code_b: str
    usage_a: int
    usage_b: int
    name_sim: float
    quote_sim: float
    combined_sim: float
    example_a: str
    example_b: str

    @property
    def key(self) -> str:
        return pair_key(self.guid_a, self.guid_b)


def _clean_text(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.replace("\r\n", "\n").replace("\r", "\n")).strip()
    return normalized


def _trim(text: str, max_len: int = 260) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def pair_key(guid_a: str, guid_b: str) -> str:
    left, right = sorted([guid_a.upper(), guid_b.upper()])
    return f"{left}__{right}"


def _read_internal_text(zf: zipfile.ZipFile, internal_path: str) -> str:
    rel = internal_path.replace("internal://", "").lstrip("/")
    archive_path = f"sources/{rel}"
    try:
        raw = zf.read(archive_path)
    except KeyError:
        return ""
    return raw.decode("utf-8", errors="replace")


def _iter_codes(parent: ET.Element, parent_guid: str | None, prefix: list[str]) -> list[CodeRecord]:
    records: list[CodeRecord] = []
    for code_elem in parent.findall("q:Code", NS):
        guid = code_elem.attrib.get("guid", "").upper()
        name = code_elem.attrib.get("name", "(unnamed)")
        parts = [*prefix, name]
        desc_elem = code_elem.find("q:Description", NS)
        description = (desc_elem.text or "").strip() if desc_elem is not None else ""
        record = CodeRecord(
            guid=guid,
            name=name,
            full_name=": ".join(parts),
            description=description,
            parent_guid=parent_guid,
        )
        records.append(record)
        records.extend(_iter_codes(code_elem, guid, parts))
    return records


def parse_qdpx(
    qdpx_path: Path,
    max_quotes_per_code: int,
) -> tuple[list[CodeRecord], dict[str, str | None]]:
    with zipfile.ZipFile(qdpx_path, "r") as zf:
        root = ET.fromstring(zf.read("project.qde"))

        codebook_root = root.find("q:CodeBook/q:Codes", NS)
        if codebook_root is None:
            raise ValueError("project.qde missing CodeBook/Codes")

        codes = _iter_codes(codebook_root, parent_guid=None, prefix=[])
        code_by_guid = {c.guid: c for c in codes if c.guid}
        parent_map: dict[str, str | None] = {c.guid: c.parent_guid for c in codes if c.guid}

        source_texts: dict[str, str] = {}
        for source_elem in root.findall("q:Sources/q:TextSource", NS):
            source_guid = source_elem.attrib.get("guid", "").upper()
            plain_text_path = source_elem.attrib.get("plainTextPath", "")
            source_texts[source_guid] = (
                _read_internal_text(zf, plain_text_path) if plain_text_path else ""
            )

        for source_elem in root.findall("q:Sources/q:TextSource", NS):
            source_guid = source_elem.attrib.get("guid", "").upper()
            source_text = source_texts.get(source_guid, "")
            if not source_text:
                continue

            for sel in source_elem.findall("q:PlainTextSelection", NS):
                try:
                    start = int(sel.attrib.get("startPosition", "0"))
                    end = int(sel.attrib.get("endPosition", "0"))
                except ValueError:
                    continue

                if start < 0 or end < start or end > len(source_text):
                    continue

                snippet = source_text[start:end].strip()
                if not snippet:
                    continue

                coded_guids: set[str] = set()
                for coding in sel.findall("q:Coding", NS):
                    for cref in coding.findall("q:CodeRef", NS):
                        target = cref.attrib.get("targetGUID", "").upper()
                        if target:
                            coded_guids.add(target)

                for guid in coded_guids:
                    code = code_by_guid.get(guid)
                    if code is None:
                        continue
                    if max_quotes_per_code <= 0 or len(code.quotes) < max_quotes_per_code:
                        source_name = source_elem.attrib.get("name", "(unknown document)")
                        code.quotes.append(QuoteSnippet(source_name=source_name, text=snippet))

    return codes, parent_map


def is_parent_child(guid_a: str, guid_b: str, parent_map: dict[str, str | None]) -> bool:
    a = guid_a.upper()
    b = guid_b.upper()

    cursor = parent_map.get(a)
    while cursor:
        if cursor == b:
            return True
        cursor = parent_map.get(cursor)

    cursor = parent_map.get(b)
    while cursor:
        if cursor == a:
            return True
        cursor = parent_map.get(cursor)

    return False


def build_label_text(code: CodeRecord) -> str:
    description = code.description if code.description else "(no description)"
    return f"Code: {code.name}\nPath: {code.full_name}\nDescription: {description}"


def build_quote_text(code: CodeRecord) -> str:
    if not code.quotes:
        return "No quotations assigned."
    joined = "\n".join(f"- [{q.source_name}] {q.text}" for q in code.quotes)
    return f"Quotation context for {code.full_name}:\n{joined}"


def _embedding_fingerprint(model_name: str, codes: list[CodeRecord]) -> str:
    payload: list[dict[str, str]] = []
    for code in codes:
        payload.append(
            {
                "guid": code.guid,
                "label": build_label_text(code),
                "quote": build_quote_text(code),
            }
        )
    raw = json.dumps({"model": model_name, "codes": payload}, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:20]


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ensure_lookup_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            model TEXT NOT NULL,
            text_hash TEXT NOT NULL,
            dim INTEGER NOT NULL,
            vector BLOB NOT NULL,
            updated_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            PRIMARY KEY (model, text_hash)
        )
        """
    )


def _load_vectors_from_lookup(
    conn: sqlite3.Connection,
    model_name: str,
    text_hashes: list[str],
) -> dict[str, np.ndarray]:
    if not text_hashes:
        return {}

    found: dict[str, np.ndarray] = {}
    chunk_size = 900
    for start in range(0, len(text_hashes), chunk_size):
        chunk = text_hashes[start : start + chunk_size]
        placeholders = ", ".join("?" for _ in chunk)
        query = (
            "SELECT text_hash, dim, vector FROM embeddings "
            f"WHERE model = ? AND text_hash IN ({placeholders})"
        )
        rows = conn.execute(query, [model_name, *chunk]).fetchall()
        for text_hash, dim, blob in rows:
            arr = np.frombuffer(blob, dtype=np.float32)
            if arr.size == dim:
                found[text_hash] = arr
    return found


def _store_vectors_in_lookup(
    conn: sqlite3.Connection,
    model_name: str,
    text_hashes: list[str],
    vectors: np.ndarray,
) -> None:
    payload = []
    for text_hash, vector in zip(text_hashes, vectors, strict=True):
        arr = np.asarray(vector, dtype=np.float32)
        payload.append((model_name, text_hash, int(arr.size), arr.tobytes()))

    conn.executemany(
        """
        INSERT INTO embeddings(model, text_hash, dim, vector)
        VALUES(?, ?, ?, ?)
        ON CONFLICT(model, text_hash)
        DO UPDATE SET
            dim = excluded.dim,
            vector = excluded.vector,
            updated_at_utc = strftime('%Y-%m-%dT%H:%M:%fZ','now')
        """,
        payload,
    )
    conn.commit()


def _encode_texts_with_lookup(
    model: Any,
    model_name: str,
    texts: list[str],
    stage_label: str,
    batch_size: int,
    lookup_db_path: Path,
) -> np.ndarray:
    if not texts:
        return np.empty((0, 0), dtype=np.float32)

    text_hashes = [_text_hash(text) for text in texts]
    lookup_db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(lookup_db_path)
    _ensure_lookup_schema(conn)

    loaded = _load_vectors_from_lookup(conn, model_name, text_hashes)
    cached_hits = sum(1 for h in text_hashes if h in loaded)
    missing_indices = [idx for idx, h in enumerate(text_hashes) if h not in loaded]
    CONSOLE.print(
        f"[dim]{stage_label}: cache hits {cached_hits}/{len(texts)}, "
        f"missing {len(missing_indices)}[/dim]"
    )

    if missing_indices:
        missing_texts = [texts[idx] for idx in missing_indices]
        encoded_missing = _encode_with_loader(
            model=model,
            texts=missing_texts,
            stage_label=f"{stage_label} (new)",
            batch_size=batch_size,
        )
        missing_hashes = [text_hashes[idx] for idx in missing_indices]
        _store_vectors_in_lookup(conn, model_name, missing_hashes, encoded_missing)
        for text_hash, vector in zip(missing_hashes, encoded_missing, strict=True):
            loaded[text_hash] = vector

    conn.close()
    ordered = [loaded[text_hash] for text_hash in text_hashes]
    return np.vstack(ordered).astype(np.float32, copy=False)


def _encode_with_loader(
    model: Any,
    texts: list[str],
    stage_label: str,
    batch_size: int,
) -> np.ndarray:
    if not texts:
        return np.empty((0, 0), dtype=np.float32)

    chunks: list[np.ndarray] = []
    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=CONSOLE,
        transient=False,
    ) as progress:
        task_id = progress.add_task(f"[cyan]{stage_label}", total=len(texts))
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            emb = model.encode(
                batch,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            chunks.append(np.asarray(emb, dtype=np.float32))
            progress.advance(task_id, len(batch))

    return np.vstack(chunks)


def _select_embedding_device(device_arg: str) -> str:
    requested = device_arg.strip().lower()
    if requested in {"cpu", "cuda"}:
        return requested

    # Auto mode: use CUDA only when the installed torch build supports
    # the detected GPU architecture.
    try:
        import torch
    except Exception:
        return "cpu"

    if not torch.cuda.is_available():
        return "cpu"

    try:
        major, minor = torch.cuda.get_device_capability(0)
        arch = f"sm_{major}{minor}"
        supported_arches = set(torch.cuda.get_arch_list())
    except Exception:
        return "cpu"

    if arch in supported_arches:
        return "cuda"

    CONSOLE.print(
        "[yellow]CUDA detected but unsupported by this PyTorch build "
        f"({arch} not in {sorted(supported_arches)}). Falling back to CPU.[/yellow]"
    )
    return "cpu"


def load_or_build_embeddings(
    model_name: str,
    codes: list[CodeRecord],
    cache_dir: Path,
    batch_size: int,
    device_arg: str,
) -> tuple[np.ndarray, np.ndarray]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    fp = _embedding_fingerprint(model_name, codes)
    cache_path = cache_dir / f"{fp}.npz"

    if cache_path.exists():
        data = np.load(cache_path, allow_pickle=False)
        CONSOLE.print(f"[green]Loaded embedding cache:[/green] {cache_path}")
        return data["label_embeddings"], data["quote_embeddings"]

    from sentence_transformers import SentenceTransformer
    lookup_db_path = cache_dir / DEFAULT_LOOKUP_DB

    started_at = time.time()
    device = _select_embedding_device(device_arg)
    CONSOLE.print(
        f"[cyan]Loading embedding model:[/cyan] {model_name} [dim](device={device})[/dim]"
    )
    model = SentenceTransformer(model_name, device=device)
    label_texts = [build_label_text(c) for c in codes]
    quote_texts = [build_quote_text(c) for c in codes]

    try:
        label_arr = _encode_texts_with_lookup(
            model=model,
            model_name=model_name,
            texts=label_texts,
            stage_label="Embedding code names/paths/descriptions",
            batch_size=batch_size,
            lookup_db_path=lookup_db_path,
        )
        quote_arr = _encode_texts_with_lookup(
            model=model,
            model_name=model_name,
            texts=quote_texts,
            stage_label="Embedding quotation context",
            batch_size=batch_size,
            lookup_db_path=lookup_db_path,
        )
    except RuntimeError as exc:
        msg = str(exc)
        if device == "cuda" and "no kernel image is available" in msg.lower():
            CONSOLE.print(
                "[yellow]GPU execution failed (CUDA kernel unsupported). "
                "Retrying embeddings on CPU...[/yellow]"
            )
            model = SentenceTransformer(model_name, device="cpu")
            label_arr = _encode_texts_with_lookup(
                model=model,
                model_name=model_name,
                texts=label_texts,
                stage_label="Embedding code names/paths/descriptions [CPU retry]",
                batch_size=batch_size,
                lookup_db_path=lookup_db_path,
            )
            quote_arr = _encode_texts_with_lookup(
                model=model,
                model_name=model_name,
                texts=quote_texts,
                stage_label="Embedding quotation context [CPU retry]",
                batch_size=batch_size,
                lookup_db_path=lookup_db_path,
            )
        else:
            raise

    np.savez_compressed(cache_path, label_embeddings=label_arr, quote_embeddings=quote_arr)
    elapsed = time.time() - started_at
    CONSOLE.print(f"[green]Saved embedding cache:[/green] {cache_path} ({elapsed:.1f}s)")
    return label_arr, quote_arr


def generate_candidates(
    codes: list[CodeRecord],
    parent_map: dict[str, str | None],
    label_embeddings: np.ndarray,
    quote_embeddings: np.ndarray,
    min_name_sim: float,
    min_quote_sim: float,
    min_combined_sim: float,
    weight_name: float,
    weight_quote: float,
    exclude_parent_child: bool,
    exclude_uncoded: bool,
    top_n: int,
) -> list[Candidate]:
    if not np.isclose(weight_name + weight_quote, 1.0):
        raise ValueError("weight_name + weight_quote must be 1.0")

    n = len(codes)
    candidates: list[Candidate] = []

    def _example_text(snippet: QuoteSnippet | None) -> str:
        if snippet is None:
            return "(no quotations)"
        return f"[{snippet.source_name}] {snippet.text}"

    for i in range(n):
        for j in range(i + 1, n):
            code_i = codes[i]
            code_j = codes[j]

            if exclude_uncoded and (code_i.usage_count == 0 or code_j.usage_count == 0):
                continue

            if exclude_parent_child and is_parent_child(code_i.guid, code_j.guid, parent_map):
                continue

            name_sim = float(np.dot(label_embeddings[i], label_embeddings[j]))
            quote_sim = float(np.dot(quote_embeddings[i], quote_embeddings[j]))
            combined = (weight_name * name_sim) + (weight_quote * quote_sim)

            if name_sim < min_name_sim or quote_sim < min_quote_sim or combined < min_combined_sim:
                continue

            candidates.append(
                Candidate(
                    guid_a=code_i.guid,
                    guid_b=code_j.guid,
                    code_a=code_i.full_name,
                    code_b=code_j.full_name,
                    usage_a=code_i.usage_count,
                    usage_b=code_j.usage_count,
                    name_sim=name_sim,
                    quote_sim=quote_sim,
                    combined_sim=combined,
                    example_a=_example_text(code_i.quotes[0] if code_i.quotes else None),
                    example_b=_example_text(code_j.quotes[0] if code_j.quotes else None),
                )
            )

    candidates.sort(key=lambda c: c.combined_sim, reverse=True)
    if top_n > 0:
        candidates = candidates[:top_n]
    return candidates


def load_state(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return {"cursor": 0, "decisions": {}, "history": []}
    return json.loads(state_path.read_text(encoding="utf-8"))


def save_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(state_path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(state_path)


def normalize_decisions(raw: Any) -> dict[str, dict[str, str]]:
    normalized: dict[str, dict[str, str]] = {}
    if not isinstance(raw, dict):
        return normalized

    for key, value in raw.items():
        if isinstance(value, dict):
            decision = str(value.get("decision", "")).strip().lower()
            mode = str(value.get("mode", "")).strip().lower()
            canonical_name = str(value.get("canonical_name", "")).strip()
            if decision == "separate":
                normalized[str(key)] = {
                    "decision": "separate",
                    "mode": "separate",
                    "canonical_name": "",
                }
            elif decision == "merge" and mode in {"keep_a", "keep_b", "custom"}:
                normalized[str(key)] = {
                    "decision": "merge",
                    "mode": mode,
                    "canonical_name": canonical_name,
                }
            continue

        if isinstance(value, str):
            v = value.strip().lower()
            if v in {"separate", "s"}:
                normalized[str(key)] = {
                    "decision": "separate",
                    "mode": "separate",
                    "canonical_name": "",
                }
            elif v in {"accept", "a"}:
                normalized[str(key)] = {
                    "decision": "merge",
                    "mode": "keep_a",
                    "canonical_name": "",
                }

    return normalized


def decision_is_reviewed(decision: dict[str, str] | None) -> bool:
    if not decision:
        return False
    return decision.get("decision") in {"merge", "separate"}


def decision_display(decision: dict[str, str] | None) -> str:
    if not decision_is_reviewed(decision):
        return ""
    if decision is None:
        return ""
    if decision.get("decision") == "separate":
        return "separate"
    mode = decision.get("mode")
    if mode == "keep_a":
        return "merge:keep_a"
    if mode == "keep_b":
        return "merge:keep_b"
    if mode == "custom":
        name = decision.get("canonical_name", "").strip()
        return f"merge:custom:{name}" if name else "merge:custom"
    return "merge"


def resolved_name(candidate: Candidate, decision: dict[str, str] | None) -> str:
    if not decision or decision.get("decision") != "merge":
        return ""
    mode = decision.get("mode")
    if mode == "keep_a":
        return candidate.code_a
    if mode == "keep_b":
        return candidate.code_b
    if mode == "custom":
        return decision.get("canonical_name", "").strip()
    return ""


def export_candidates_csv(
    candidates: list[Candidate], decisions: dict[str, dict[str, str]], out_path: Path
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "code_a",
                "code_b",
                "guid_a",
                "guid_b",
                "usage_a",
                "usage_b",
                "name_sim",
                "quote_sim",
                "combined_sim",
                "decision",
                "resolved_name",
                "example_a",
                "example_b",
            ]
        )
        for c in candidates:
            writer.writerow(
                [
                    c.code_a,
                    c.code_b,
                    c.guid_a,
                    c.guid_b,
                    c.usage_a,
                    c.usage_b,
                    f"{c.name_sim:.4f}",
                    f"{c.quote_sim:.4f}",
                    f"{c.combined_sim:.4f}",
                    decision_display(decisions.get(c.key)),
                    resolved_name(c, decisions.get(c.key)),
                    c.example_a,
                    c.example_b,
                ]
            )


def export_review_csv(
    candidates: list[Candidate],
    decisions: dict[str, dict[str, str]],
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "decision",
                "resolved_name",
                "code_a",
                "code_b",
                "guid_a",
                "guid_b",
                "combined_sim",
                "name_sim",
                "quote_sim",
                "usage_a",
                "usage_b",
            ]
        )
        for c in candidates:
            decision = decisions.get(c.key)
            if not decision_is_reviewed(decision):
                continue
            writer.writerow(
                [
                    decision_display(decision),
                    resolved_name(c, decision),
                    c.code_a,
                    c.code_b,
                    c.guid_a,
                    c.guid_b,
                    f"{c.combined_sim:.4f}",
                    f"{c.name_sim:.4f}",
                    f"{c.quote_sim:.4f}",
                    c.usage_a,
                    c.usage_b,
                ]
            )


def export_review_md(
    candidates: list[Candidate],
    decisions: dict[str, dict[str, str]],
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged = [c for c in candidates if decisions.get(c.key, {}).get("decision") == "merge"]
    separate = [c for c in candidates if decisions.get(c.key, {}).get("decision") == "separate"]

    lines: list[str] = []
    lines.append("# QDPX Code Deduplication Review")
    lines.append("")
    lines.append(f"- Accepted dedupe suggestions: **{len(merged)}**")
    lines.append(f"- Kept separate: **{len(separate)}**")
    lines.append("")

    lines.append("## Accepted")
    lines.append("")
    for c in merged:
        target = resolved_name(c, decisions.get(c.key))
        lines.append(
            f"- `{c.code_a}` <-> `{c.code_b}` "
            f"-> `{target}` "
            f"(combined={c.combined_sim:.3f}, name={c.name_sim:.3f}, quote={c.quote_sim:.3f})"
        )
    if not merged:
        lines.append("- *(none)*")
    lines.append("")

    lines.append("## Suggested Merge Names")
    lines.append("")
    for c in merged:
        target = resolved_name(c, decisions.get(c.key))
        lines.append(f"- `{target}` <= `{c.code_a}` + `{c.code_b}`")
    if not merged:
        lines.append("- *(none)*")
    lines.append("")

    lines.append("## Kept Separate")
    lines.append("")
    for c in separate:
        lines.append(
            f"- `{c.code_a}` <-> `{c.code_b}` "
            f"(combined={c.combined_sim:.3f}, name={c.name_sim:.3f}, quote={c.quote_sim:.3f})"
        )
    if not separate:
        lines.append("- *(none)*")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


class DedupeApp(App[None]):
    BINDINGS = [
        Binding("j", "next_candidate", "Next"),
        Binding("k", "prev_candidate", "Prev"),
        Binding("t", "show_table", "Table"),
        Binding("v", "show_compare", "Compare"),
        Binding("escape", "show_compare", "Back"),
        Binding("]", "scroll_panels_down", "Scroll Down"),
        Binding("[", "scroll_panels_up", "Scroll Up"),
        Binding("a", "merge_keep_a", "Keep A"),
        Binding("b", "merge_keep_b", "Keep B"),
        Binding("c", "merge_custom", "Custom Name"),
        Binding("s", "separate_candidate", "Separate"),
        Binding("z", "undo", "Undo"),
        Binding("e", "export_now", "Export"),
        Binding("q", "quit", "Quit"),
    ]

    CSS = """
    Screen {
      layout: vertical;
    }
    #compare-view {
      height: 1fr;
      display: block;
    }
    #body {
      display: none;
      height: 0;
    }
    #scorebar {
      height: auto;
      min-height: 5;
      border: round $accent;
      padding: 1;
      margin: 0 0 1 0;
      background: $panel;
    }
    #compare-body {
      layout: horizontal;
      height: 1fr;
      display: block;
    }
    #left-code {
      width: 1fr;
      height: 1fr;
      border: round $primary;
      padding: 1;
      margin: 0 1 0 0;
      background: $surface;
    }
    #right-code {
      width: 1fr;
      height: 1fr;
      border: round $primary;
      padding: 1;
      background: $surface;
    }
    #left-content {
      width: 100%;
      height: auto;
    }
    #right-content {
      width: 100%;
      height: auto;
    }
    #table {
      display: none;
      height: 1fr;
      border: round $accent;
    }
    .table-mode #compare-view {
      display: none;
    }
    .table-mode #table {
      display: block;
      height: 1fr;
    }
    .table-mode #body {
      display: block;
      height: 1fr;
    }
    """

    def __init__(
        self,
        candidates: list[Candidate],
        state_path: Path,
        candidates_csv: Path,
        review_csv: Path,
        review_md: Path,
        code_lookup: dict[str, CodeRecord],
        base_qdpx: Path,
        apply_out_qdpx: Path,
        apply_on_export: bool,
        initial_state: dict[str, Any],
    ) -> None:
        super().__init__()
        self.candidates = candidates
        self.state_path = state_path
        self.candidates_csv = candidates_csv
        self.review_csv = review_csv
        self.review_md = review_md
        self.code_lookup = code_lookup
        self.base_qdpx = base_qdpx
        self.apply_out_qdpx = apply_out_qdpx
        self.apply_on_export = apply_on_export
        self.state = initial_state
        self.decisions = normalize_decisions(initial_state.get("decisions", {}))
        self.history: list[dict[str, Any]] = list(initial_state.get("history", []))
        self.current_index = int(initial_state.get("cursor", 0)) if candidates else 0
        self.in_table_mode = False
        if self.current_index >= len(candidates):
            self.current_index = max(0, len(candidates) - 1)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="compare-view"):
            yield Static(id="scorebar", markup=False)
            with Horizontal(id="compare-body"):
                with VerticalScroll(id="left-code"):
                    yield Static(id="left-content")
                with VerticalScroll(id="right-code"):
                    yield Static(id="right-content")
        with Horizontal(id="body"):
            yield DataTable(id="table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#table", DataTable)
        table.cursor_type = "row"
        table.add_columns("#", "Decision", "Combined", "Name", "Quote", "Code A", "Code B")

        for idx, candidate in enumerate(self.candidates, start=1):
            table.add_row(
                str(idx),
                self._decision_mark(candidate.key),
                f"{candidate.combined_sim:.3f}",
                f"{candidate.name_sim:.3f}",
                f"{candidate.quote_sim:.3f}",
                _trim(candidate.code_a, 42),
                _trim(candidate.code_b, 42),
            )

        if self.candidates:
            self._sync_cursor(save=False)
        self._save_state()

    def _decision_mark(self, key: str) -> str:
        d = self.decisions.get(key)
        if not d:
            return ""
        if d.get("decision") == "separate":
            return "S"
        mode = d.get("mode")
        if mode == "keep_a":
            return "A"
        if mode == "keep_b":
            return "B"
        if mode == "custom":
            return "C"
        return ""

    def _sync_cursor(self, save: bool = True) -> None:
        if not self.candidates:
            self.query_one("#scorebar", Static).update(
                "No candidates match the current thresholds."
            )
            self.query_one("#left-content", Static).update("")
            self.query_one("#right-content", Static).update("")
            return

        table = self.query_one("#table", DataTable)
        table.move_cursor(row=self.current_index, column=0)
        self.query_one("#left-code", VerticalScroll).scroll_home(animate=False)
        self.query_one("#right-code", VerticalScroll).scroll_home(animate=False)
        self._render_compare()
        if save:
            self._save_state()

    def _render_compare(self) -> None:
        scorebar = self.query_one("#scorebar", Static)
        left_panel = self.query_one("#left-content", Static)
        right_panel = self.query_one("#right-content", Static)
        if not self.candidates:
            scorebar.update("No candidates.")
            left_panel.update("")
            right_panel.update("")
            return

        c = self.candidates[self.current_index]
        decision = decision_display(self.decisions.get(c.key)) or "(none)"
        resolved = resolved_name(c, self.decisions.get(c.key))
        reviewed = len([v for v in self.decisions.values() if decision_is_reviewed(v)])
        score_text = (
            f"Candidate {self.current_index + 1}/{len(self.candidates)}   "
            f"Reviewed {reviewed}/{len(self.candidates)}\n"
            f"Decision {decision}   "
            f"Merged name {resolved or '(n/a)'}\n"
            f"Scores combined={c.combined_sim:.4f} | "
            f"name={c.name_sim:.4f} | quote={c.quote_sim:.4f}\n"
            "Mode "
            f"{'table' if self.in_table_mode else 'compare'} "
            "(t table, v/esc compare, [ and ] scroll)"
        )
        scorebar.update(score_text)

        code_a = self.code_lookup.get(c.guid_a)
        code_b = self.code_lookup.get(c.guid_b)
        current_decision = self.decisions.get(c.key)
        shared_quote_keys: set[str] = set()
        if code_a and code_b:
            keys_a = {
                f"{q.source_name}\n{q.text.strip()}" for q in code_a.quotes if q.text.strip()
            }
            keys_b = {
                f"{q.source_name}\n{q.text.strip()}" for q in code_b.quotes if q.text.strip()
            }
            shared_quote_keys = keys_a.intersection(keys_b)

        left_panel.update(
            self._format_code_panel(
                "Code A",
                c.code_a,
                c.usage_a,
                code_a,
                panel_key="a",
                decision=current_decision,
                shared_quote_keys=shared_quote_keys,
            )
        )
        right_panel.update(
            self._format_code_panel(
                "Code B",
                c.code_b,
                c.usage_b,
                code_b,
                panel_key="b",
                decision=current_decision,
                shared_quote_keys=shared_quote_keys,
            )
        )

    def _header_color_for_panel(
        self,
        panel_key: str,
        decision: dict[str, str] | None,
    ) -> str:
        if not decision:
            return "cyan"
        if decision.get("decision") != "merge":
            return "cyan"

        mode = decision.get("mode")
        if mode == "keep_a":
            return "green" if panel_key == "a" else "red"
        if mode == "keep_b":
            return "green" if panel_key == "b" else "red"
        return "cyan"

    def _format_code_panel(
        self,
        panel_title: str,
        fallback_name: str,
        usage_count: int,
        code: CodeRecord | None,
        panel_key: str,
        decision: dict[str, str] | None,
        shared_quote_keys: set[str],
    ) -> str:
        header_color = self._header_color_for_panel(panel_key=panel_key, decision=decision)

        if code is None:
            return (
                f"[bold {header_color}]{escape(panel_title)} {escape(fallback_name)} "
                f"(quotes: {usage_count})[/bold {header_color}]\n\n"
                "[dim](no code details available)[/dim]"
            )

        quotes = code.quotes

        lines: list[str] = []
        lines.append(
            f"[bold {header_color}]{escape(panel_title)} {escape(code.full_name)} "
            f"(quotes: {len(quotes)})[/bold {header_color}]"
        )
        lines.append("")

        if not quotes:
            lines.append("(no quotations)")
        else:
            for idx, quote in enumerate(quotes, start=1):
                quote_key = f"{quote.source_name}\n{quote.text.strip()}"
                is_shared = quote_key in shared_quote_keys
                header_style = "bold yellow" if is_shared else "bold"
                text_prefix = "[yellow]" if is_shared else ""
                text_suffix = "[/yellow]" if is_shared else ""
                lines.append(
                    f"[{header_style}]Quote {idx}: {escape(quote.source_name)}[/{header_style}]"
                )
                lines.append(f"{text_prefix}{escape(quote.text)}{text_suffix}")
                lines.append("")
        return "\n".join(lines).rstrip()

    def _save_state(self) -> None:
        self.state["cursor"] = self.current_index
        self.state["decisions"] = self.decisions
        self.state["history"] = self.history[-1000:]
        save_state(self.state_path, self.state)

    def _record_decision_obj(self, decision: dict[str, str], auto_advance: bool = True) -> None:
        if not self.candidates:
            return
        c = self.candidates[self.current_index]
        key = c.key
        previous = self.decisions.get(key)
        self.history.append({"index": self.current_index, "key": key, "previous": previous})
        self.decisions[key] = decision

        table = self.query_one("#table", DataTable)
        table.update_cell_at(cast(Any, (self.current_index, 1)), self._decision_mark(key))

        if auto_advance and self.current_index < len(self.candidates) - 1:
            self.current_index += 1

        self._render_compare()
        self._save_state()

    def action_next_candidate(self) -> None:
        if not self.candidates:
            return
        self.current_index = min(self.current_index + 1, len(self.candidates) - 1)
        self._sync_cursor()

    def action_prev_candidate(self) -> None:
        if not self.candidates:
            return
        self.current_index = max(self.current_index - 1, 0)
        self._sync_cursor()

    def action_show_table(self) -> None:
        self.in_table_mode = True
        self.add_class("table-mode")
        table = self.query_one("#table", DataTable)
        table.focus()
        self._render_compare()

    def action_show_compare(self) -> None:
        self.in_table_mode = False
        self.remove_class("table-mode")
        self._render_compare()

    def action_scroll_panels_down(self) -> None:
        if self.in_table_mode:
            return
        self.query_one("#left-code", VerticalScroll).scroll_relative(y=6)
        self.query_one("#right-code", VerticalScroll).scroll_relative(y=6)

    def action_scroll_panels_up(self) -> None:
        if self.in_table_mode:
            return
        self.query_one("#left-code", VerticalScroll).scroll_relative(y=-6)
        self.query_one("#right-code", VerticalScroll).scroll_relative(y=-6)

    def action_merge_keep_a(self) -> None:
        self._record_decision_obj({"decision": "merge", "mode": "keep_a", "canonical_name": ""})

    def action_merge_keep_b(self) -> None:
        self._record_decision_obj({"decision": "merge", "mode": "keep_b", "canonical_name": ""})

    def action_merge_custom(self) -> None:
        if not self.candidates:
            return
        c = self.candidates[self.current_index]
        default_name = resolved_name(c, self.decisions.get(c.key)) or c.code_a
        self.push_screen(
            RenameScreen(default_name),
            callback=self._apply_custom_name,
        )

    def _apply_custom_name(self, value: str | None) -> None:
        if value is None:
            return
        cleaned = value.strip()
        if not cleaned:
            self.notify("Custom name cannot be empty.", severity="warning", timeout=2.0)
            return
        self._record_decision_obj(
            {"decision": "merge", "mode": "custom", "canonical_name": cleaned}
        )

    def action_separate_candidate(self) -> None:
        self._record_decision_obj(
            {"decision": "separate", "mode": "separate", "canonical_name": ""}
        )

    def action_undo(self) -> None:
        if not self.history:
            return
        entry = self.history.pop()
        index = int(entry.get("index", 0))
        key = str(entry.get("key", ""))
        previous_raw = entry.get("previous")

        if isinstance(previous_raw, dict) and decision_is_reviewed(previous_raw):
            previous = cast(dict[str, str], previous_raw)
            self.decisions[key] = previous
        else:
            self.decisions.pop(key, None)

        if self.candidates:
            self.current_index = max(0, min(index, len(self.candidates) - 1))
            table = self.query_one("#table", DataTable)
            table.update_cell_at(cast(Any, (self.current_index, 1)), self._decision_mark(key))
        self._sync_cursor()

    def action_export_now(self) -> None:
        export_candidates_csv(self.candidates, self.decisions, self.candidates_csv)
        export_review_csv(self.candidates, self.decisions, self.review_csv)
        export_review_md(self.candidates, self.decisions, self.review_md)
        if self.apply_on_export:
            try:
                merge_count = sum(
                    1
                    for decision in self.decisions.values()
                    if isinstance(decision, dict) and decision.get("decision") == "merge"
                )
                if merge_count > 0:
                    apply_decisions_to_qdpx(
                        base_qdpx=self.base_qdpx,
                        review_csv=self.review_csv,
                        out_qdpx=self.apply_out_qdpx,
                    )
                    self.notify(
                        f"Applied {merge_count} merge decision(s) to {self.apply_out_qdpx}",
                        timeout=2.5,
                    )
                else:
                    self.notify("No merge decisions yet; skipped QDPX apply step.", timeout=2.5)
            except Exception as exc:  # pragma: no cover - defensive runtime UX path
                self.notify(f"QDPX apply failed: {exc}", severity="error", timeout=4.0)
        self.notify(
            f"Exported to {self.candidates_csv}, {self.review_csv}, {self.review_md}",
            timeout=2.5,
        )

    async def action_quit(self) -> None:
        self._save_state()
        export_candidates_csv(self.candidates, self.decisions, self.candidates_csv)
        export_review_csv(self.candidates, self.decisions, self.review_csv)
        export_review_md(self.candidates, self.decisions, self.review_md)
        self.exit()


class RenameScreen(ModalScreen[str | None]):
    CSS = """
    RenameScreen {
      align: center middle;
    }
    #rename-box {
      width: 80;
      height: 7;
      border: round $primary;
      padding: 1;
      background: $surface;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, default_name: str) -> None:
        super().__init__()
        self.default_name = default_name

    def compose(self) -> ComposeResult:
        yield Static("Enter merged code name and press Enter:", id="rename-box")
        yield Input(value=self.default_name, id="rename-input")

    def on_mount(self) -> None:
        self.query_one("#rename-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)


def _find_qdpx_candidates(workspace_root: Path) -> list[Path]:
    qdpx_dir = workspace_root / "qdpx"
    candidates: list[Path] = []
    if qdpx_dir.exists():
        candidates.extend(qdpx_dir.glob("*.qdpx"))
    candidates.extend(workspace_root.glob("*.qdpx"))

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)

    deduped.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return deduped


def _pick_qdpx_interactive(candidates: list[Path], workspace_root: Path) -> Path:
    if not candidates:
        raise SystemExit("No .qdpx file found in ./qdpx or workspace root.")
    if len(candidates) == 1:
        return candidates[0]

    if not sys.stdin.isatty():
        print("No --qdpx provided and no interactive terminal; using newest .qdpx file.")
        return candidates[0]

    print("Select a QDPX file:")
    for idx, candidate in enumerate(candidates, start=1):
        try:
            rel = candidate.resolve().relative_to(workspace_root.resolve())
            display = str(rel)
        except ValueError:
            display = str(candidate)
        print(f"  {idx}) {display}")

    while True:
        raw = input(f"Enter number [1-{len(candidates)}] (blank=1): ").strip()
        if raw == "":
            return candidates[0]
        try:
            selected = int(raw)
        except ValueError:
            print("Please enter a valid number.")
            continue
        if 1 <= selected <= len(candidates):
            return candidates[selected - 1]
        print("Selection out of range.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find and review likely duplicate QDPX codes in a Rich TUI."
    )
    parser.add_argument(
        "--qdpx",
        type=Path,
        default=None,
        help="Path to .qdpx file (if omitted, interactive selection is shown)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help="Local embedding model name",
    )
    parser.add_argument(
        "--min-name-sim",
        type=float,
        default=0.55,
        help="Minimum name/path similarity",
    )
    parser.add_argument(
        "--min-quote-sim",
        type=float,
        default=0.50,
        help="Minimum quote-context similarity",
    )
    parser.add_argument(
        "--min-combined-sim",
        type=float,
        default=0.58,
        help="Minimum weighted similarity",
    )
    parser.add_argument(
        "--weight-name",
        type=float,
        default=0.45,
        help="Weight for name similarity",
    )
    parser.add_argument(
        "--weight-quote",
        type=float,
        default=0.55,
        help="Weight for quote similarity",
    )
    parser.add_argument("--top", type=int, default=500, help="Maximum candidates to review")
    parser.add_argument(
        "--max-quotes-per-code",
        type=int,
        default=0,
        help="Max quotations included per code (0 means all)",
    )
    parser.add_argument(
        "--exclude-parent-child",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Exclude parent-child code pairs",
    )
    parser.add_argument(
        "--exclude-uncoded",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Exclude pairs where either code has zero quotations",
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=DEFAULT_STATE_PATH,
        help="JSON state file for resume",
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Load existing review state",
    )
    parser.add_argument("--candidates-csv", type=Path, default=DEFAULT_CANDIDATES_CSV)
    parser.add_argument("--review-csv", type=Path, default=DEFAULT_REVIEW_CSV)
    parser.add_argument("--review-md", type=Path, default=DEFAULT_REVIEW_MD)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument(
        "--apply-on-export",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply dedupe decisions into a new QDPX when exporting",
    )
    parser.add_argument(
        "--apply-out",
        type=Path,
        default=None,
        help="Output QDPX path for apply-on-export (default: sibling *-deduped.qdpx)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Embedding device selection",
    )
    parser.add_argument(
        "--embed-batch-size",
        type=int,
        default=24,
        help="Embedding batch size (lower if memory issues)",
    )
    parser.add_argument("--no-tui", action="store_true", help="Only compute and export candidates")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace_root = Path(__file__).resolve().parent.parent
    qdpx_path = (
        args.qdpx.resolve()
        if args.qdpx
        else _pick_qdpx_interactive(_find_qdpx_candidates(workspace_root), workspace_root)
    )

    apply_out_qdpx = (
        args.apply_out.resolve()
        if args.apply_out
        else qdpx_path.with_name(f"{qdpx_path.stem}-deduped.qdpx")
    )

    if not qdpx_path.exists():
        raise SystemExit(f"QDPX not found: {qdpx_path}")
    if not np.isclose(args.weight_name + args.weight_quote, 1.0):
        raise SystemExit("weight-name + weight-quote must equal 1.0")

    print("Reading QDPX...")
    codes, parent_map = parse_qdpx(qdpx_path, max_quotes_per_code=args.max_quotes_per_code)
    print(f"Loaded {len(codes)} codes")

    print(f"Embedding with model: {args.model}")
    label_emb, quote_emb = load_or_build_embeddings(
        args.model,
        codes,
        args.cache_dir,
        batch_size=max(1, args.embed_batch_size),
        device_arg=args.device,
    )

    print("Generating candidates...")
    candidates = generate_candidates(
        codes=codes,
        parent_map=parent_map,
        label_embeddings=label_emb,
        quote_embeddings=quote_emb,
        min_name_sim=args.min_name_sim,
        min_quote_sim=args.min_quote_sim,
        min_combined_sim=args.min_combined_sim,
        weight_name=args.weight_name,
        weight_quote=args.weight_quote,
        exclude_parent_child=args.exclude_parent_child,
        exclude_uncoded=args.exclude_uncoded,
        top_n=args.top,
    )
    print(f"Candidate pairs: {len(candidates)}")

    state = load_state(args.state) if args.resume else {"cursor": 0, "decisions": {}, "history": []}
    decisions = normalize_decisions(state.get("decisions", {}))

    export_candidates_csv(candidates, decisions, args.candidates_csv)
    export_review_csv(candidates, decisions, args.review_csv)
    export_review_md(candidates, decisions, args.review_md)

    if args.no_tui:
        print(f"Wrote: {args.candidates_csv}")
        print(f"Wrote: {args.review_csv}")
        print(f"Wrote: {args.review_md}")
        return 0

    app = DedupeApp(
        candidates=candidates,
        state_path=args.state,
        candidates_csv=args.candidates_csv,
        review_csv=args.review_csv,
        review_md=args.review_md,
        code_lookup={c.guid: c for c in codes if c.guid},
        base_qdpx=qdpx_path,
        apply_out_qdpx=apply_out_qdpx,
        apply_on_export=args.apply_on_export,
        initial_state=state,
    )
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
