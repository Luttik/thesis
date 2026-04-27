#!/usr/bin/env python3
"""Search QDPX codes by embedding similarity in a small TUI."""

from __future__ import annotations

import argparse
import threading
from pathlib import Path

import numpy as np
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import DataTable, Footer, Header, Input, Static

from thesis_cli.qdpx_dedupe_tui import (
    CodeRecord,
    _find_qdpx_candidates,
    _pick_qdpx_interactive,
    _select_embedding_device,
    load_or_build_embeddings,
    parse_qdpx,
)

DEFAULT_MODEL = "BAAI/bge-m3"
DEFAULT_CACHE_DIR = Path(".cache/qdpx-dedupe")


def rank_code_matches(
    *,
    query: str,
    codes: list[CodeRecord],
    q_vector: np.ndarray,
    label_embeddings: np.ndarray,
    quote_embeddings: np.ndarray,
    weight_name: float,
    weight_quote: float,
    top_n: int,
) -> tuple[list[int], list[float]]:
    scores_name = label_embeddings @ q_vector
    scores_quote = quote_embeddings @ q_vector
    scores = (weight_name * scores_name) + (weight_quote * scores_quote)

    # Lexical boost so exact/near-exact code text is always easy to find.
    ql = query.strip().lower()
    if ql:
        for idx, code in enumerate(codes):
            name_l = code.name.lower()
            full_l = code.full_name.lower()
            desc_l = code.description.lower()
            quote_l = "\n".join(q.text for q in code.quotes).lower()
            if ql == name_l or ql == full_l:
                scores[idx] += 5.0
            elif ql in full_l or ql in name_l:
                scores[idx] += 0.4
            elif ql in desc_l:
                scores[idx] += 0.3
            elif ql in quote_l:
                scores[idx] += 0.2

    order = np.argsort(scores)[::-1]
    if top_n > 0:
        order = order[:top_n]

    indices = [int(i) for i in order]
    values = [float(scores[i]) for i in order]
    return indices, values


class CodeSearchApp(App[None]):
    BINDINGS = [
        Binding("j", "next_row", "Next"),
        Binding("k", "prev_row", "Prev"),
        Binding("down", "next_row", "Next"),
        Binding("up", "prev_row", "Prev"),
        Binding("/", "focus_query", "Query"),
        Binding("q", "quit", "Quit"),
    ]

    CSS = """
    Screen {
      layout: vertical;
    }
    #query-wrap {
      height: auto;
      border: round $accent;
      padding: 1;
      margin: 0 0 1 0;
    }
    #body {
      layout: horizontal;
      height: 1fr;
    }
    #results {
      width: 52%;
      height: 1fr;
      border: round $primary;
      margin: 0 1 0 0;
    }
    #detail-scroll {
      width: 48%;
      height: 1fr;
      border: round $primary;
      padding: 1;
    }
    #detail {
      width: 100%;
      height: auto;
    }
    """

    def __init__(
        self,
        codes: list[CodeRecord],
        label_embeddings: np.ndarray,
        quote_embeddings: np.ndarray,
        model_name: str,
        query_batch_size: int,
        weight_name: float,
        weight_quote: float,
        initial_query: str,
        top_n: int,
        device: str,
    ) -> None:
        super().__init__()
        self.codes = codes
        self.label_embeddings = label_embeddings
        self.quote_embeddings = quote_embeddings
        self.model_name = model_name
        self.query_batch_size = max(1, query_batch_size)
        self.weight_name = weight_name
        self.weight_quote = weight_quote
        self.initial_query = initial_query
        self.top_n = top_n
        self.device = device
        self.model = None
        self._model_lock = threading.Lock()
        self._search_generation = 0
        self.result_indices: list[int] = []
        self.result_scores: list[float] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="query-wrap"):
            yield Static("Type search text and press Enter:")
            yield Input(
                value=self.initial_query,
                placeholder="e.g. campaign automation",
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
        table.add_columns("Code", "Match")
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

            indices, values = rank_code_matches(
                query=query,
                codes=self.codes,
                q_vector=q_vector,
                label_embeddings=self.label_embeddings,
                quote_embeddings=self.quote_embeddings,
                weight_name=self.weight_name,
                weight_quote=self.weight_quote,
                top_n=self.top_n,
            )
            self.call_from_thread(self._apply_search_results, generation, query, indices, values)
        except Exception as exc:  # pragma: no cover - runtime guard
            self.call_from_thread(self._apply_search_error, generation, str(exc))

    def _apply_search_results(
        self,
        generation: int,
        query: str,
        indices: list[int],
        values: list[float],
    ) -> None:
        if generation != self._search_generation:
            return

        self.result_indices = indices
        self.result_scores = values
        self._render_results()

        self.query_one("#query-status", Static).update(
            f"Ready. {len(indices)} result(s) for: {query}"
        )

    def _apply_search_error(self, generation: int, message: str) -> None:
        if generation != self._search_generation:
            return

        self.query_one("#query-status", Static).update(f"Search failed: {message}")

    def _render_results(self) -> None:
        table = self.query_one("#results", DataTable)
        table.clear(columns=False)
        ranked = zip(self.result_indices, self.result_scores, strict=True)
        for idx, score in ranked:
            pct = max(0.0, min(0.99, score))
            pct_text = f"{int(round(pct * 100)):02d}%"
            table.add_row(self.codes[idx].full_name, pct_text)

        if self.result_indices:
            table.move_cursor(row=0, column=0)
            self._render_detail(0)
        else:
            self.query_one("#detail", Static).update("No results.")

    def _render_detail(self, result_row: int) -> None:
        detail = self.query_one("#detail", Static)
        if not self.result_indices or result_row >= len(self.result_indices):
            detail.update("No result selected.")
            return

        idx = self.result_indices[result_row]
        score = self.result_scores[result_row]
        code = self.codes[idx]

        lines: list[str] = []
        lines.append(f"[bold cyan]{code.full_name}[/bold cyan]")
        lines.append(f"Score: {score:.4f}")
        lines.append(f"Quotes: {len(code.quotes)}")
        lines.append("")

        if code.quotes:
            for q_idx, quote in enumerate(code.quotes, start=1):
                lines.append(f"[bold]Quote {q_idx}: {quote.source_name}[/bold]")
                lines.append(quote.text)
                lines.append("")
        else:
            lines.append("(no quotations)")

        if code.description.strip():
            lines.append("[bold]Description[/bold]")
            lines.append(code.description.strip())

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
        if not self.result_indices:
            return
        row, _ = table.cursor_coordinate
        next_row = min(row + 1, len(self.result_indices) - 1)
        table.move_cursor(row=next_row, column=0)
        self._render_detail(next_row)

    def action_prev_row(self) -> None:
        table = self.query_one("#results", DataTable)
        if not self.result_indices:
            return
        row, _ = table.cursor_coordinate
        prev_row = max(row - 1, 0)
        table.move_cursor(row=prev_row, column=0)
        self._render_detail(prev_row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search QDPX codes with embedding similarity.")
    parser.add_argument(
        "--qdpx",
        type=Path,
        default=None,
        help="Path to .qdpx file (if omitted, interactive selection is shown)",
    )
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--query", type=str, default="")
    parser.add_argument("--top", type=int, default=300)
    parser.add_argument("--weight-name", type=float, default=0.5)
    parser.add_argument("--weight-quote", type=float, default=0.5)
    parser.add_argument("--max-quotes-per-code", type=int, default=0)
    parser.add_argument("--embed-batch-size", type=int, default=24)
    parser.add_argument("--query-batch-size", type=int, default=16)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not np.isclose(args.weight_name + args.weight_quote, 1.0):
        raise SystemExit("weight-name + weight-quote must equal 1.0")

    workspace_root = Path(__file__).resolve().parent.parent
    qdpx_path = (
        args.qdpx.resolve()
        if args.qdpx
        else _pick_qdpx_interactive(_find_qdpx_candidates(workspace_root), workspace_root)
    )
    if not qdpx_path.exists():
        raise SystemExit(f"QDPX not found: {qdpx_path}")

    print("Reading QDPX...")
    codes, _ = parse_qdpx(qdpx_path, max_quotes_per_code=args.max_quotes_per_code)
    print(f"Loaded {len(codes)} codes")

    print("Preparing code embeddings...")
    label_emb, quote_emb = load_or_build_embeddings(
        model_name=args.model,
        codes=codes,
        cache_dir=args.cache_dir,
        batch_size=max(1, args.embed_batch_size),
        device_arg=args.device,
    )
    device = _select_embedding_device(args.device)

    app = CodeSearchApp(
        codes=codes,
        label_embeddings=label_emb,
        quote_embeddings=quote_emb,
        model_name=args.model,
        query_batch_size=max(1, args.query_batch_size),
        weight_name=args.weight_name,
        weight_quote=args.weight_quote,
        initial_query=args.query,
        top_n=args.top,
        device=device,
    )
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
