#!/usr/bin/env python3
"""Search QDPX document paragraphs with local vector similarity."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import threading
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import DataTable, Footer, Header, Input, Static

from thesis_cli.qdpx_dedupe_tui import (
    _encode_texts_with_lookup,
    _find_qdpx_candidates,
    _pick_qdpx_interactive,
    _select_embedding_device,
)

QDA_NS = "urn:QDA-XML:project:1.0"
NS = {"q": QDA_NS}

DEFAULT_MODEL = "BAAI/bge-m3"
DEFAULT_CACHE_DIR = Path(".cache/qdpx-paragraph-vast")
DEFAULT_LOOKUP_DB = "embedding_lookup.sqlite"


@dataclass
class SourceDoc:
    guid: str
    name: str
    text: str


@dataclass
class SelectionRecord:
    source_guid: str
    start: int
    end: int
    code_names: list[str]


@dataclass
class ParagraphRecord:
    paragraph_id: int
    source_guid: str
    source_name: str
    paragraph_index: int
    start: int
    end: int
    speaker: str
    text: str
    quote_hits: int
    codes: list[str]


@dataclass
class IndexPaths:
    fingerprint: str
    db_path: Path
    emb_path: Path
    meta_path: Path


@dataclass
class SearchHit:
    record: ParagraphRecord
    score: float


def _read_internal_text(zf: zipfile.ZipFile, internal_path: str) -> str:
    rel = internal_path.replace("internal://", "").lstrip("/")
    archive_path = f"sources/{rel}"
    try:
        raw = zf.read(archive_path)
    except KeyError:
        return ""
    return raw.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")


def _iter_code_paths(parent: ET.Element, prefix: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for code_elem in parent.findall("q:Code", NS):
        guid = code_elem.attrib.get("guid", "").upper()
        name = code_elem.attrib.get("name", "(unnamed)")
        full = ": ".join([*prefix, name])
        if guid:
            out[guid] = full
        out.update(_iter_code_paths(code_elem, [*prefix, name]))
    return out


def _parse_qdpx_sources_and_selections(
    qdpx_path: Path,
) -> tuple[list[SourceDoc], list[SelectionRecord]]:
    with zipfile.ZipFile(qdpx_path, "r") as zf:
        root = ET.fromstring(zf.read("project.qde"))

        codebook_root = root.find("q:CodeBook/q:Codes", NS)
        if codebook_root is None:
            raise SystemExit("project.qde missing CodeBook/Codes")
        code_map = _iter_code_paths(codebook_root, [])

        source_texts: dict[str, str] = {}
        source_names: dict[str, str] = {}
        source_elems = root.findall("q:Sources/q:TextSource", NS)
        for source_elem in source_elems:
            source_guid = source_elem.attrib.get("guid", "").upper()
            source_name = source_elem.attrib.get("name", "(unknown document)")
            plain_text_path = source_elem.attrib.get("plainTextPath", "")
            source_names[source_guid] = source_name
            source_texts[source_guid] = (
                _read_internal_text(zf, plain_text_path) if plain_text_path else ""
            )

        sources: list[SourceDoc] = []
        selections: list[SelectionRecord] = []
        for source_elem in source_elems:
            source_guid = source_elem.attrib.get("guid", "").upper()
            source_name = source_names.get(source_guid, "(unknown document)")
            source_text = source_texts.get(source_guid, "")
            sources.append(SourceDoc(guid=source_guid, name=source_name, text=source_text))

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

                code_names: list[str] = []
                seen: set[str] = set()
                for coding in sel.findall("q:Coding", NS):
                    for cref in coding.findall("q:CodeRef", NS):
                        guid = cref.attrib.get("targetGUID", "").upper()
                        if not guid or guid in seen:
                            continue
                        seen.add(guid)
                        code_names.append(code_map.get(guid, guid))

                selections.append(
                    SelectionRecord(
                        source_guid=source_guid,
                        start=start,
                        end=end,
                        code_names=code_names,
                    )
                )

    return sources, selections


def _extract_speaker(text: str) -> str:
    stripped = text.lstrip()
    if stripped.startswith("[Me]"):
        return "Me"
    if stripped.startswith("[Them]"):
        return "Them"
    return "Unknown"


def split_source_paragraphs(source: SourceDoc) -> list[tuple[int, int, int, str, str]]:
    paragraphs: list[tuple[int, int, int, str, str]] = []
    cursor = 0
    para_idx = 0
    for raw_line in source.text.splitlines(keepends=True):
        line = raw_line.rstrip("\n")
        content = line.rstrip()
        if not content.strip():
            cursor += len(raw_line)
            continue

        left_trim = len(content) - len(content.lstrip())
        start = cursor + left_trim
        end = cursor + len(content)
        text = source.text[start:end]
        paragraphs.append((para_idx, start, end, _extract_speaker(text), text))
        para_idx += 1
        cursor += len(raw_line)
    return paragraphs


def _has_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return min(a_end, b_end) > max(a_start, b_start)


def build_paragraph_records(qdpx_path: Path) -> list[ParagraphRecord]:
    sources, selections = _parse_qdpx_sources_and_selections(qdpx_path)
    sel_by_source: dict[str, list[SelectionRecord]] = {}
    for sel in selections:
        sel_by_source.setdefault(sel.source_guid, []).append(sel)

    out: list[ParagraphRecord] = []
    paragraph_id = 0
    for source in sources:
        spans = split_source_paragraphs(source)
        source_selections = sel_by_source.get(source.guid, [])
        for para_idx, start, end, speaker, text in spans:
            code_set: set[str] = set()
            quote_hits = 0
            for sel in source_selections:
                if not _has_overlap(start, end, sel.start, sel.end):
                    continue
                quote_hits += 1
                code_set.update(sel.code_names)

            out.append(
                ParagraphRecord(
                    paragraph_id=paragraph_id,
                    source_guid=source.guid,
                    source_name=source.name,
                    paragraph_index=para_idx,
                    start=start,
                    end=end,
                    speaker=speaker,
                    text=text,
                    quote_hits=quote_hits,
                    codes=sorted(code_set),
                )
            )
            paragraph_id += 1
    return out


def _index_paths(qdpx_path: Path, cache_dir: Path, model_name: str) -> IndexPaths:
    stat = qdpx_path.stat()
    key = (
        f"{qdpx_path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}|{model_name}".encode("utf-8")
    )
    fp = hashlib.sha256(key).hexdigest()[:20]
    cache_dir.mkdir(parents=True, exist_ok=True)
    return IndexPaths(
        fingerprint=fp,
        db_path=cache_dir / f"{fp}.sqlite",
        emb_path=cache_dir / f"{fp}.npy",
        meta_path=cache_dir / f"{fp}.json",
    )


def _write_index_db(db_path: Path, records: list[ParagraphRecord]) -> None:
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE paragraphs (
            paragraph_id INTEGER PRIMARY KEY,
            source_guid TEXT NOT NULL,
            source_name TEXT NOT NULL,
            paragraph_index INTEGER NOT NULL,
            start_pos INTEGER NOT NULL,
            end_pos INTEGER NOT NULL,
            speaker TEXT NOT NULL,
            quote_hits INTEGER NOT NULL,
            text TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE paragraph_codes (
            paragraph_id INTEGER NOT NULL,
            code_name TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX idx_paragraphs_source ON paragraphs(source_name)")
    conn.execute("CREATE INDEX idx_paragraphs_speaker ON paragraphs(speaker)")
    conn.execute("CREATE INDEX idx_codes_name ON paragraph_codes(code_name)")

    conn.executemany(
        """
        INSERT INTO paragraphs(
            paragraph_id, source_guid, source_name, paragraph_index,
            start_pos, end_pos, speaker, quote_hits, text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                rec.paragraph_id,
                rec.source_guid,
                rec.source_name,
                rec.paragraph_index,
                rec.start,
                rec.end,
                rec.speaker,
                rec.quote_hits,
                rec.text,
            )
            for rec in records
        ],
    )

    rows: list[tuple[int, str]] = []
    for rec in records:
        for code_name in rec.codes:
            rows.append((rec.paragraph_id, code_name))
    if rows:
        conn.executemany(
            "INSERT INTO paragraph_codes(paragraph_id, code_name) VALUES(?, ?)",
            rows,
        )

    conn.commit()
    conn.close()


def build_index(
    *,
    qdpx_path: Path,
    cache_dir: Path,
    model_name: str,
    device_arg: str,
    batch_size: int,
    force: bool,
) -> IndexPaths:
    paths = _index_paths(qdpx_path, cache_dir, model_name)
    if (
        not force
        and paths.db_path.exists()
        and paths.emb_path.exists()
        and paths.meta_path.exists()
    ):
        return paths

    print("Reading QDPX and extracting paragraphs...")
    records = build_paragraph_records(qdpx_path)
    texts = [r.text for r in records]
    print(f"Prepared {len(records)} paragraphs")

    from sentence_transformers import SentenceTransformer

    resolved_device = _select_embedding_device(device_arg)
    print(f"Loading embedding model: {model_name} (device={resolved_device})")
    model = SentenceTransformer(model_name, device=resolved_device)
    lookup_db = cache_dir / DEFAULT_LOOKUP_DB
    embeddings = _encode_texts_with_lookup(
        model=model,
        model_name=model_name,
        texts=texts,
        stage_label="Embedding paragraphs",
        batch_size=max(1, batch_size),
        lookup_db_path=lookup_db,
    )
    embeddings = np.asarray(embeddings, dtype=np.float32)

    _write_index_db(paths.db_path, records)
    np.save(paths.emb_path, embeddings)
    meta = {
        "fingerprint": paths.fingerprint,
        "qdpx_path": str(qdpx_path.resolve()),
        "model": model_name,
        "paragraphs": len(records),
        "embedding_dim": int(embeddings.shape[1]) if embeddings.ndim == 2 else 0,
    }
    paths.meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote index DB: {paths.db_path}")
    print(f"Wrote embedding matrix: {paths.emb_path}")
    return paths


def _load_records(db_path: Path) -> list[ParagraphRecord]:
    conn = sqlite3.connect(db_path)
    paragraphs_rows = conn.execute(
        """
        SELECT paragraph_id, source_guid, source_name, paragraph_index,
               start_pos, end_pos, speaker, quote_hits, text
        FROM paragraphs
        ORDER BY paragraph_id ASC
        """
    ).fetchall()
    code_rows = conn.execute(
        "SELECT paragraph_id, code_name FROM paragraph_codes ORDER BY paragraph_id ASC"
    ).fetchall()
    conn.close()

    code_map: dict[int, list[str]] = {}
    for paragraph_id, code_name in code_rows:
        code_map.setdefault(int(paragraph_id), []).append(str(code_name))

    records: list[ParagraphRecord] = []
    for row in paragraphs_rows:
        paragraph_id = int(row[0])
        records.append(
            ParagraphRecord(
                paragraph_id=paragraph_id,
                source_guid=str(row[1]),
                source_name=str(row[2]),
                paragraph_index=int(row[3]),
                start=int(row[4]),
                end=int(row[5]),
                speaker=str(row[6]),
                quote_hits=int(row[7]),
                text=str(row[8]),
                codes=code_map.get(paragraph_id, []),
            )
        )
    return records


def _load_index(paths: IndexPaths) -> tuple[list[ParagraphRecord], np.ndarray]:
    records = _load_records(paths.db_path)
    emb = np.load(paths.emb_path)
    emb = np.asarray(emb, dtype=np.float32)
    if emb.ndim != 2:
        raise SystemExit(f"Invalid embedding matrix shape: {emb.shape}")
    if emb.shape[0] != len(records):
        raise SystemExit(
            f"Index mismatch: {len(records)} paragraph rows but {emb.shape[0]} embedding rows"
        )
    return records, emb


def _query_vector(model_name: str, device: str, query: str, batch_size: int) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name, device=device)
    vector = model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
        batch_size=max(1, batch_size),
    )[0]
    return np.asarray(vector, dtype=np.float32)


def _matches_filters(
    rec: ParagraphRecord,
    *,
    doc_filter: str,
    speaker_filter: str,
    code_filter: str,
) -> bool:
    if doc_filter and doc_filter not in rec.source_name.lower():
        return False
    if speaker_filter != "any" and rec.speaker.lower() != speaker_filter:
        return False
    if code_filter:
        return any(code_filter in code.lower() for code in rec.codes)
    return True


def rank_paragraphs(
    *,
    query: str,
    q_vector: np.ndarray,
    records: list[ParagraphRecord],
    embeddings: np.ndarray,
    top_n: int,
    doc_filter: str,
    speaker_filter: str,
    code_filter: str,
) -> list[SearchHit]:
    if embeddings.size == 0 or not records:
        return []

    scores = embeddings @ q_vector
    ql = query.strip().lower()
    order = np.argsort(scores)[::-1]

    hits: list[SearchHit] = []
    for idx in order:
        rec = records[int(idx)]
        if not _matches_filters(
            rec,
            doc_filter=doc_filter,
            speaker_filter=speaker_filter,
            code_filter=code_filter,
        ):
            continue

        score = float(scores[int(idx)])
        if ql:
            text_l = rec.text.lower()
            if ql in text_l:
                score += 0.12
            elif any(ql in c.lower() for c in rec.codes):
                score += 0.18
            elif ql in rec.source_name.lower():
                score += 0.08

        hits.append(SearchHit(record=rec, score=score))

    hits.sort(key=lambda h: h.score, reverse=True)
    if top_n > 0:
        hits = hits[:top_n]
    return hits


def related_for_paragraph(
    *,
    paragraph_id: int,
    records: list[ParagraphRecord],
    embeddings: np.ndarray,
    top_n: int,
) -> list[SearchHit]:
    if paragraph_id < 0 or paragraph_id >= len(records):
        return []
    base = embeddings[paragraph_id]
    scores = embeddings @ base
    order = np.argsort(scores)[::-1]

    hits: list[SearchHit] = []
    for idx in order:
        i = int(idx)
        if i == paragraph_id:
            continue
        hits.append(SearchHit(record=records[i], score=float(scores[i])))
        if top_n > 0 and len(hits) >= top_n:
            break
    return hits


class ParagraphVastApp(App[None]):
    BINDINGS = [
        Binding("j", "next_row", "Next"),
        Binding("k", "prev_row", "Prev"),
        Binding("down", "next_row", "Next"),
        Binding("up", "prev_row", "Prev"),
        Binding("/", "focus_query", "Query"),
        Binding("q", "quit", "Quit"),
    ]

    CSS = """
    Screen { layout: vertical; }
    #query-wrap { height: auto; border: round $accent; padding: 1; margin: 0 0 1 0; }
    #body { layout: horizontal; height: 1fr; }
    #results { width: 52%; height: 1fr; border: round $primary; margin: 0 1 0 0; }
    #detail-scroll { width: 48%; height: 1fr; border: round $primary; padding: 1; }
    #detail { width: 100%; height: auto; }
    """

    def __init__(
        self,
        *,
        records: list[ParagraphRecord],
        embeddings: np.ndarray,
        model_name: str,
        device: str,
        query_batch_size: int,
        top_n: int,
        initial_query: str,
    ) -> None:
        super().__init__()
        self.records = records
        self.embeddings = embeddings
        self.model_name = model_name
        self.device = device
        self.query_batch_size = max(1, query_batch_size)
        self.top_n = max(1, top_n)
        self.initial_query = initial_query

        self._search_generation = 0
        self._model_lock = threading.Lock()
        self.model = None

        self.result_ids: list[int] = []
        self.result_scores: list[float] = []
        self.by_id = {r.paragraph_id: r for r in records}
        self.by_source_and_idx = {(r.source_guid, r.paragraph_index): r for r in records}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="query-wrap"):
            yield Static("Type search text and press Enter:")
            yield Input(
                value=self.initial_query,
                placeholder="e.g. onboarding volunteers",
                id="query",
            )
            yield Static("Ready.", id="query-status")
        with Horizontal(id="body"):
            yield DataTable(id="results")
            with VerticalScroll(id="detail-scroll"):
                yield Static(id="detail")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#results", DataTable)
        table.cursor_type = "row"
        table.add_columns("Doc", "P#", "Match")
        self.query_one("#query", Input).focus()
        if self.initial_query.strip():
            self._schedule_search(self.initial_query.strip())

    def _get_model(self):
        with self._model_lock:
            if self.model is None:
                from sentence_transformers import SentenceTransformer

                self.model = SentenceTransformer(self.model_name, device=self.device)
        return self.model

    def _schedule_search(self, query: str) -> None:
        self._search_generation += 1
        generation = self._search_generation
        self.query_one("#query-status", Static).update(f"Searching for: {query}")
        thread = threading.Thread(
            target=self._run_search_background,
            args=(query, generation),
            daemon=True,
        )
        thread.start()

    def _run_search_background(self, query: str, generation: int) -> None:
        try:
            model = self._get_model()
            q_vector = model.encode(
                [query],
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
                batch_size=self.query_batch_size,
            )[0]
            hits = rank_paragraphs(
                query=query,
                q_vector=np.asarray(q_vector, dtype=np.float32),
                records=self.records,
                embeddings=self.embeddings,
                top_n=self.top_n,
                doc_filter="",
                speaker_filter="any",
                code_filter="",
            )
            ids = [h.record.paragraph_id for h in hits]
            scores = [h.score for h in hits]
            self.call_from_thread(self._apply_search_results, generation, query, ids, scores)
        except Exception as exc:  # pragma: no cover
            self.call_from_thread(self._apply_search_error, generation, str(exc))

    def _apply_search_results(
        self,
        generation: int,
        query: str,
        result_ids: list[int],
        scores: list[float],
    ) -> None:
        if generation != self._search_generation:
            return
        self.result_ids = result_ids
        self.result_scores = scores
        self._render_results()
        self.query_one("#query-status", Static).update(
            f"Ready. {len(result_ids)} result(s) for: {query}"
        )

    def _apply_search_error(self, generation: int, message: str) -> None:
        if generation != self._search_generation:
            return
        self.query_one("#query-status", Static).update(f"Search failed: {message}")

    def _render_results(self) -> None:
        table = self.query_one("#results", DataTable)
        table.clear(columns=False)
        for paragraph_id, score in zip(self.result_ids, self.result_scores, strict=True):
            rec = self.by_id.get(paragraph_id)
            if rec is None:
                continue
            pct = max(0.0, min(0.99, score))
            table.add_row(
                rec.source_name[:42],
                str(rec.paragraph_index),
                f"{int(round(pct * 100)):02d}%",
            )

        if self.result_ids:
            table.move_cursor(row=0, column=0)
            self._render_detail(0)
        else:
            self.query_one("#detail", Static).update("No results.")

    def _render_detail(self, result_row: int) -> None:
        detail = self.query_one("#detail", Static)
        if not self.result_ids or result_row >= len(self.result_ids):
            detail.update("No result selected.")
            return

        paragraph_id = self.result_ids[result_row]
        score = self.result_scores[result_row]
        rec = self.by_id.get(paragraph_id)
        if rec is None:
            detail.update("Result not found.")
            return

        prev_rec = self.by_source_and_idx.get((rec.source_guid, rec.paragraph_index - 1))
        next_rec = self.by_source_and_idx.get((rec.source_guid, rec.paragraph_index + 1))
        related = related_for_paragraph(
            paragraph_id=rec.paragraph_id,
            records=self.records,
            embeddings=self.embeddings,
            top_n=4,
        )

        lines: list[str] = []
        lines.append(f"[bold cyan]{rec.source_name}[/bold cyan] | paragraph {rec.paragraph_index}")
        lines.append(f"Span {rec.start}:{rec.end} | Speaker {rec.speaker} | Match {score:.4f}")
        lines.append(f"Overlapping quotations: {rec.quote_hits}")
        lines.append("")
        lines.append("[bold]Codes[/bold]")
        lines.append(", ".join(rec.codes) if rec.codes else "(none)")
        lines.append("")
        lines.append("[bold]Current paragraph[/bold]")
        lines.append(rec.text)
        lines.append("")
        lines.append("[dim]Before[/dim]")
        lines.append(prev_rec.text if prev_rec else "(none)")
        lines.append("")
        lines.append("[dim]After[/dim]")
        lines.append(next_rec.text if next_rec else "(none)")
        lines.append("")
        lines.append("[bold]Related paragraphs[/bold]")
        if related:
            for hit in related:
                lines.append(
                    f"- {hit.record.source_name} p{hit.record.paragraph_index} ({hit.score:.3f})"
                )
                lines.append(f"  {hit.record.text[:180]}")
        else:
            lines.append("(none)")
        detail.update("\n".join(lines).rstrip())

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "query":
            return
        query = event.value.strip()
        if not query:
            return
        self._schedule_search(query)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id != "results":
            return
        row = event.cursor_row
        if row is None or row < 0:
            return
        self._render_detail(row)

    def action_focus_query(self) -> None:
        query = self.query_one("#query", Input)
        query.value = ""
        query.focus()
        self.query_one("#query-status", Static).update("Ready. Enter text and press Enter.")

    def action_next_row(self) -> None:
        table = self.query_one("#results", DataTable)
        if not self.result_ids:
            return
        row, _ = table.cursor_coordinate
        next_row = min(row + 1, len(self.result_ids) - 1)
        table.move_cursor(row=next_row, column=0)
        self._render_detail(next_row)

    def action_prev_row(self) -> None:
        table = self.query_one("#results", DataTable)
        if not self.result_ids:
            return
        row, _ = table.cursor_coordinate
        prev_row = max(row - 1, 0)
        table.move_cursor(row=prev_row, column=0)
        self._render_detail(prev_row)


def _resolve_qdpx_path(arg_qdpx: Path | None) -> Path:
    workspace_root = Path(__file__).resolve().parent.parent
    return (
        arg_qdpx.resolve()
        if arg_qdpx
        else _pick_qdpx_interactive(_find_qdpx_candidates(workspace_root), workspace_root)
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local vector search over QDPX document paragraphs."
    )
    parser.add_argument(
        "--qdpx",
        type=Path,
        default=None,
        help="Path to .qdpx file (if omitted, interactive selection is shown)",
    )
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--embed-batch-size", type=int, default=24)
    parser.add_argument("--query-batch-size", type=int, default=16)

    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="Build local paragraph vector index")
    p_index.add_argument("--force", action=argparse.BooleanOptionalAction, default=False)

    p_search = sub.add_parser("search", help="Search paragraphs by semantic similarity")
    p_search.add_argument("--query", type=str, required=True)
    p_search.add_argument("--top", type=int, default=20)
    p_search.add_argument("--doc", type=str, default="")
    p_search.add_argument(
        "--speaker",
        type=str,
        default="any",
        choices=["any", "me", "them", "unknown"],
    )
    p_search.add_argument("--code", type=str, default="")

    p_tui = sub.add_parser("tui", help="Interactive two-way paragraph search TUI")
    p_tui.add_argument("--query", type=str, default="")
    p_tui.add_argument("--top", type=int, default=200)

    return parser.parse_args()


def _ensure_index(args: argparse.Namespace, qdpx_path: Path, force: bool = False) -> IndexPaths:
    return build_index(
        qdpx_path=qdpx_path,
        cache_dir=args.cache_dir,
        model_name=args.model,
        device_arg=args.device,
        batch_size=max(1, args.embed_batch_size),
        force=force,
    )


def _run_search(args: argparse.Namespace, records: list[ParagraphRecord], emb: np.ndarray) -> int:
    query = args.query.strip()
    if not query:
        raise SystemExit("--query cannot be empty")

    device = _select_embedding_device(args.device)
    q_vector = _query_vector(
        model_name=args.model,
        device=device,
        query=query,
        batch_size=max(1, args.query_batch_size),
    )
    hits = rank_paragraphs(
        query=query,
        q_vector=q_vector,
        records=records,
        embeddings=emb,
        top_n=max(1, args.top),
        doc_filter=args.doc.strip().lower(),
        speaker_filter=args.speaker.strip().lower(),
        code_filter=args.code.strip().lower(),
    )
    if not hits:
        print("No matches found.")
        return 0

    for rank, hit in enumerate(hits, start=1):
        rec = hit.record
        code_text = ", ".join(rec.codes[:4])
        if len(rec.codes) > 4:
            code_text += ", ..."
        print(
            f"{rank:02d}. score={hit.score:.4f} id={rec.paragraph_id} "
            f"doc={rec.source_name} p={rec.paragraph_index} "
            f"span={rec.start}:{rec.end} speaker={rec.speaker}"
        )
        print(f"    {rec.text[:220]}")
        if code_text:
            print(f"    codes: {code_text}")
    return 0


def main() -> int:
    args = parse_args()
    qdpx_path = _resolve_qdpx_path(args.qdpx)
    if not qdpx_path.exists():
        raise SystemExit(f"QDPX not found: {qdpx_path}")

    if args.command == "index":
        _ensure_index(args, qdpx_path, force=bool(args.force))
        return 0

    paths = _ensure_index(args, qdpx_path, force=False)
    records, emb = _load_index(paths)

    if args.command == "search":
        return _run_search(args, records, emb)

    if args.command == "tui":
        device = _select_embedding_device(args.device)
        app = ParagraphVastApp(
            records=records,
            embeddings=emb,
            model_name=args.model,
            device=device,
            query_batch_size=max(1, args.query_batch_size),
            top_n=max(1, args.top),
            initial_query=args.query,
        )
        app.run()
        return 0

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
