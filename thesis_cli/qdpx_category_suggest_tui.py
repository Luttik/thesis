#!/usr/bin/env python3
"""Suggest top-level parent categories for uncategorised codes."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import DataTable, Footer, Header, Input, Static

from thesis_cli.qdpx_category_apply import apply_category_decisions_to_qdpx
from thesis_cli.qdpx_dedupe_tui import (
    DEFAULT_LOOKUP_DB,
    CodeRecord,
    _encode_texts_with_lookup,
    _find_qdpx_candidates,
    _pick_qdpx_interactive,
    _select_embedding_device,
    build_label_text,
    parse_qdpx,
)

DEFAULT_MODEL = "BAAI/bge-m3"
DEFAULT_CACHE_DIR = Path(".cache/qdpx-dedupe")
DEFAULT_SUGGESTIONS_CSV = Path("output/qdpx-category-suggestions.csv")
DEFAULT_REVIEW_CSV = Path("output/qdpx-category-review.csv")
DEFAULT_REVIEW_MD = Path("output/qdpx-category-review.md")
DEFAULT_STATE = Path("output/qdpx-category-review.json")


@dataclass
class CategoryCandidate:
    code_guid: str
    code_name: str
    code_quotes: int
    parent_guid: str
    parent_name: str
    score: float


def _children_map(codes: list[CodeRecord]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for code in codes:
        if not code.parent_guid:
            continue
        mapping.setdefault(code.parent_guid, []).append(code.guid)
    return mapping


def _collect_descendants(root_guid: str, child_map: dict[str, list[str]]) -> list[str]:
    out: list[str] = []
    stack = list(child_map.get(root_guid, []))
    while stack:
        guid = stack.pop()
        out.append(guid)
        stack.extend(child_map.get(guid, []))
    return out


def _uncategorised_codes(
    codes: list[CodeRecord],
    child_map: dict[str, list[str]],
) -> list[CodeRecord]:
    return [
        code
        for code in codes
        if code.parent_guid is None and code.guid not in child_map and code.usage_count > 0
    ]


def _parent_categories(
    codes: list[CodeRecord],
    child_map: dict[str, list[str]],
) -> list[CodeRecord]:
    return [code for code in codes if code.parent_guid is None and code.guid in child_map]


def _code_profile_text(code: CodeRecord) -> str:
    lines = [build_label_text(code)]
    if code.quotes:
        lines.append("Quotes:")
        for quote in code.quotes:
            lines.append(f"- [{quote.source_name}] {quote.text}")
    return "\n".join(lines)


def _parent_profile_text(
    parent: CodeRecord,
    child_map: dict[str, list[str]],
    code_by_guid: dict[str, CodeRecord],
) -> str:
    descendants = _collect_descendants(parent.guid, child_map)
    lines = [
        f"Parent category: {parent.full_name}",
        f"Description: {parent.description or '(no description)'}",
    ]
    if descendants:
        lines.append("Children:")
        for guid in descendants:
            child = code_by_guid.get(guid)
            if child is None:
                continue
            lines.append(f"- {child.full_name}")
        lines.append("Quotes:")
        quote_count = 0
        for guid in descendants:
            child = code_by_guid.get(guid)
            if child is None:
                continue
            for quote in child.quotes:
                lines.append(f"- [{quote.source_name}] {quote.text}")
                quote_count += 1
                if quote_count >= 40:
                    break
            if quote_count >= 40:
                break
    return "\n".join(lines)


def _build_similarity(
    model_name: str,
    cache_dir: Path,
    device: str,
    batch_size: int,
    uncategorised: list[CodeRecord],
    parents: list[CodeRecord],
    child_map: dict[str, list[str]],
    code_by_guid: dict[str, CodeRecord],
) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    resolved_device = _select_embedding_device(device)
    print(f"Loading embedding model on {resolved_device}...")
    model = SentenceTransformer(model_name, device=resolved_device)

    cache_dir.mkdir(parents=True, exist_ok=True)
    lookup_db = cache_dir / DEFAULT_LOOKUP_DB
    uncat_texts = [_code_profile_text(code) for code in uncategorised]
    parent_texts = [
        _parent_profile_text(parent, child_map=child_map, code_by_guid=code_by_guid)
        for parent in parents
    ]

    uncat_emb = _encode_texts_with_lookup(
        model=model,
        model_name=model_name,
        texts=uncat_texts,
        stage_label="Embedding uncategorised codes",
        batch_size=batch_size,
        lookup_db_path=lookup_db,
    )
    parent_emb = _encode_texts_with_lookup(
        model=model,
        model_name=model_name,
        texts=parent_texts,
        stage_label="Embedding parent categories",
        batch_size=batch_size,
        lookup_db_path=lookup_db,
    )
    return uncat_emb @ parent_emb.T


def _rank_for_code(scores_row: np.ndarray, top_n: int) -> list[int]:
    order = list(np.argsort(scores_row)[::-1])
    if top_n > 0:
        order = order[:top_n]
    return [int(v) for v in order]


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"cursor": 0, "decisions": {}, "history": []}
    return cast(dict[str, Any], __import__("json").loads(path.read_text(encoding="utf-8")))


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(__import__("json").dumps(state, indent=2), encoding="utf-8")
    tmp.replace(path)


def _export_suggestions_csv(
    out_path: Path,
    uncategorised: list[CodeRecord],
    parents: list[CodeRecord],
    sim: np.ndarray,
    top_k: int,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["code_guid", "code_name", "parent_guid", "parent_name", "score"])
        for idx, code in enumerate(uncategorised):
            ranked = _rank_for_code(sim[idx], top_k)
            for parent_idx in ranked:
                parent = parents[parent_idx]
                writer.writerow(
                    [
                        code.guid,
                        code.full_name,
                        parent.guid,
                        parent.full_name,
                        f"{float(sim[idx, parent_idx]):.4f}",
                    ]
                )


def _export_review_csv(
    out_path: Path,
    uncategorised: list[CodeRecord],
    parents_by_guid: dict[str, CodeRecord],
    decisions: dict[str, str],
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "status",
                "code_guid",
                "code_name",
                "selected_parent_guid",
                "selected_parent_name",
            ]
        )
        for code in uncategorised:
            parent_guid = decisions.get(code.guid, "")
            if parent_guid:
                parent = parents_by_guid.get(parent_guid)
                writer.writerow(
                    [
                        "assigned",
                        code.guid,
                        code.full_name,
                        parent_guid,
                        parent.full_name if parent else "",
                    ]
                )
            else:
                writer.writerow(["skipped", code.guid, code.full_name, "", ""])


def _export_review_md(
    out_path: Path,
    uncategorised: list[CodeRecord],
    parents_by_guid: dict[str, CodeRecord],
    decisions: dict[str, str],
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    assigned = [
        (code, decisions.get(code.guid, ""))
        for code in uncategorised
        if decisions.get(code.guid, "")
    ]
    skipped = [code for code in uncategorised if not decisions.get(code.guid, "")]

    lines: list[str] = []
    lines.append("# QDPX Category Assignment Review")
    lines.append("")
    lines.append(f"- Assigned: **{len(assigned)}**")
    lines.append(f"- Skipped: **{len(skipped)}**")
    lines.append("")
    lines.append("## Assigned")
    lines.append("")
    for code, parent_guid in assigned:
        parent = parents_by_guid.get(parent_guid)
        parent_name = parent.full_name if parent else parent_guid
        lines.append(f"- `{code.full_name}` -> `{parent_name}`")
    if not assigned:
        lines.append("- *(none)*")
    lines.append("")
    lines.append("## Skipped")
    lines.append("")
    for code in skipped:
        lines.append(f"- `{code.full_name}`")
    if not skipped:
        lines.append("- *(none)*")
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


class CategorySuggestApp(App[None]):
    BINDINGS = [
        Binding("j", "next_code", "Next"),
        Binding("k", "prev_code", "Prev"),
        Binding("down", "next_code", "Next"),
        Binding("up", "prev_code", "Prev"),
        Binding("a", "assign_rank_1", "Assign #1"),
        Binding("b", "assign_rank_2", "Assign #2"),
        Binding("c", "assign_rank_3", "Assign #3"),
        Binding("d", "assign_rank_4", "Assign #4"),
        Binding("e", "export_and_apply", "Save"),
        Binding("s", "skip_code", "Skip"),
        Binding("z", "undo", "Undo"),
        Binding("/", "focus_filter", "Filter"),
        Binding("q", "quit", "Quit"),
    ]

    CSS = """
    Screen { layout: vertical; }
    #top { height: auto; border: round $accent; padding: 1; margin: 0 0 1 0; }
    #body { layout: horizontal; height: 1fr; }
    #left { width: 56%; height: 1fr; border: round $primary; padding: 1; margin: 0 1 0 0; }
    #right { width: 44%; height: 1fr; border: round $primary; padding: 1; }
    #suggestions { height: 1fr; }
    #detail { height: 1fr; }
    """

    def __init__(
        self,
        uncategorised: list[CodeRecord],
        parents: list[CodeRecord],
        sim: np.ndarray,
        base_qdpx: Path,
        apply_out: Path,
        state_path: Path,
        suggestions_csv: Path,
        review_csv: Path,
        review_md: Path,
        initial_state: dict[str, Any],
        apply_on_export: bool,
    ) -> None:
        super().__init__()
        self.uncategorised = uncategorised
        self.parents = parents
        self.parents_by_guid = {p.guid: p for p in parents}
        self.sim = sim
        self.base_qdpx = base_qdpx
        self.apply_out = apply_out
        self.state_path = state_path
        self.suggestions_csv = suggestions_csv
        self.review_csv = review_csv
        self.review_md = review_md
        self.apply_on_export = apply_on_export

        self.decisions: dict[str, str] = cast(
            dict[str, str], initial_state.get("decisions", {})
        )
        self.history: list[dict[str, Any]] = cast(
            list[dict[str, Any]], initial_state.get("history", [])
        )
        self.current = int(initial_state.get("cursor", 0)) if self.uncategorised else 0
        if self.current >= len(self.uncategorised):
            self.current = max(0, len(self.uncategorised) - 1)
        self.filter_text = ""
        self.visible_parent_indices: list[int] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="top"):
            yield Static(id="status")
            yield Input(placeholder="Filter parents (press /)", id="filter")
        with Horizontal(id="body"):
            with VerticalScroll(id="left"):
                yield Static(id="detail")
            with Vertical(id="right"):
                yield DataTable(id="suggestions")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#suggestions", DataTable)
        table.cursor_type = "row"
        table.add_columns("Rank", "Parent", "Score")
        self.query_one("#filter", Input).value = ""
        self._render()

    def _filtered_parent_indices(self) -> list[int]:
        if not self.parents:
            return []
        row = self.sim[self.current]
        ranked = _rank_for_code(row, top_n=0)
        if not self.filter_text:
            return ranked[:8]

        ft = self.filter_text.lower()
        out: list[int] = []
        for idx in ranked:
            parent = self.parents[idx]
            if ft in parent.full_name.lower() or ft in parent.name.lower():
                out.append(idx)
            if len(out) >= 8:
                break
        return out

    def _render(self) -> None:
        if not self.uncategorised:
            self.query_one("#status", Static).update("No uncategorised coded leaf codes found.")
            self.query_one("#detail", Static).update("")
            return

        code = self.uncategorised[self.current]
        selected_parent_guid = self.decisions.get(code.guid, "")
        selected_parent_name = (
            self.parents_by_guid[selected_parent_guid].full_name
            if selected_parent_guid in self.parents_by_guid
            else "(none)"
        )
        assigned_count = len([v for v in self.decisions.values() if v])
        self.query_one("#status", Static).update(
            "Code "
            f"{self.current + 1}/{len(self.uncategorised)}   "
            f"Assigned {assigned_count}/{len(self.uncategorised)}   "
            f"Selected parent: {selected_parent_name}"
        )

        lines = [
            f"[bold cyan]{code.full_name}[/bold cyan]",
            f"Quotes: {len(code.quotes)}",
            "",
        ]
        for idx, quote in enumerate(code.quotes, start=1):
            lines.append(f"[bold]Quote {idx}: {quote.source_name}[/bold]")
            lines.append(quote.text)
            lines.append("")
        self.query_one("#detail", Static).update("\n".join(lines).rstrip())

        self.visible_parent_indices = self._filtered_parent_indices()
        table = self.query_one("#suggestions", DataTable)
        table.clear(columns=False)
        for rank, parent_idx in enumerate(self.visible_parent_indices, start=1):
            parent = self.parents[parent_idx]
            score = float(self.sim[self.current, parent_idx])
            table.add_row(str(rank), parent.full_name, f"{score:.4f}")
        if self.visible_parent_indices:
            table.move_cursor(row=0, column=0)

        self._save_state()

    def _save_state(self) -> None:
        _save_state(
            self.state_path,
            {
                "cursor": self.current,
                "decisions": self.decisions,
                "history": self.history[-1000:],
            },
        )

    def _assign_by_rank(self, rank: int) -> None:
        if not self.uncategorised or rank < 1 or rank > len(self.visible_parent_indices):
            return
        code = self.uncategorised[self.current]
        parent_idx = self.visible_parent_indices[rank - 1]
        parent_guid = self.parents[parent_idx].guid
        prev = self.decisions.get(code.guid, "")
        self.history.append({"idx": self.current, "guid": code.guid, "prev": prev})
        self.decisions[code.guid] = parent_guid
        if self.current < len(self.uncategorised) - 1:
            self.current += 1
        self._render()

    def action_assign_rank_1(self) -> None:
        self._assign_by_rank(1)

    def action_assign_rank_2(self) -> None:
        self._assign_by_rank(2)

    def action_assign_rank_3(self) -> None:
        self._assign_by_rank(3)

    def action_assign_rank_4(self) -> None:
        self._assign_by_rank(4)

    def action_next_code(self) -> None:
        if not self.uncategorised:
            return
        self.current = min(self.current + 1, len(self.uncategorised) - 1)
        self._render()

    def action_prev_code(self) -> None:
        if not self.uncategorised:
            return
        self.current = max(self.current - 1, 0)
        self._render()

    def action_skip_code(self) -> None:
        if not self.uncategorised:
            return
        code = self.uncategorised[self.current]
        prev = self.decisions.get(code.guid, "")
        self.history.append({"idx": self.current, "guid": code.guid, "prev": prev})
        self.decisions.pop(code.guid, None)
        if self.current < len(self.uncategorised) - 1:
            self.current += 1
        self._render()

    def action_undo(self) -> None:
        if not self.history:
            return
        entry = self.history.pop()
        idx = int(entry.get("idx", 0))
        guid = str(entry.get("guid", ""))
        prev = str(entry.get("prev", ""))
        if prev:
            self.decisions[guid] = prev
        else:
            self.decisions.pop(guid, None)
        self.current = max(0, min(idx, len(self.uncategorised) - 1))
        self._render()

    def action_focus_filter(self) -> None:
        flt = self.query_one("#filter", Input)
        flt.value = ""
        flt.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "filter":
            return
        self.filter_text = event.value.strip()
        self._render()

    def action_export_and_apply(self) -> None:
        _export_suggestions_csv(
            out_path=self.suggestions_csv,
            uncategorised=self.uncategorised,
            parents=self.parents,
            sim=self.sim,
            top_k=5,
        )
        _export_review_csv(
            out_path=self.review_csv,
            uncategorised=self.uncategorised,
            parents_by_guid=self.parents_by_guid,
            decisions=self.decisions,
        )
        _export_review_md(
            out_path=self.review_md,
            uncategorised=self.uncategorised,
            parents_by_guid=self.parents_by_guid,
            decisions=self.decisions,
        )

        if self.apply_on_export:
            try:
                if any(self.decisions.values()):
                    apply_category_decisions_to_qdpx(
                        base_qdpx=self.base_qdpx,
                        review_csv=self.review_csv,
                        out_qdpx=self.apply_out,
                    )
                    self.notify(f"Applied category assignments to {self.apply_out}", timeout=2.5)
                else:
                    self.notify(
                        "No category assignments yet; skipped QDPX apply step.",
                        timeout=2.5,
                    )
            except Exception as exc:  # pragma: no cover
                self.notify(f"Category apply failed: {exc}", severity="error", timeout=4.0)

        self.notify(
            f"Exported {self.suggestions_csv.name}, {self.review_csv.name}, {self.review_md.name}",
            timeout=2.5,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Suggest top-level parent categories for uncategorised coded leaf codes."
    )
    parser.add_argument(
        "--qdpx",
        type=Path,
        default=None,
        help="Path to .qdpx file (if omitted, interactive picker is shown)",
    )
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--embed-batch-size", type=int, default=24)
    parser.add_argument("--max-quotes-per-code", type=int, default=0)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--suggestions-csv", type=Path, default=DEFAULT_SUGGESTIONS_CSV)
    parser.add_argument("--review-csv", type=Path, default=DEFAULT_REVIEW_CSV)
    parser.add_argument("--review-md", type=Path, default=DEFAULT_REVIEW_MD)
    parser.add_argument(
        "--apply-on-export",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply assignments into a new QDPX when saving",
    )
    parser.add_argument(
        "--apply-out",
        type=Path,
        default=None,
        help="Output QDPX for apply-on-export (default: sibling *-categorized.qdpx)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace_root = Path(__file__).resolve().parent.parent
    qdpx_path = (
        args.qdpx.resolve()
        if args.qdpx
        else _pick_qdpx_interactive(_find_qdpx_candidates(workspace_root), workspace_root)
    )
    if not qdpx_path.exists():
        raise SystemExit(f"QDPX not found: {qdpx_path}")

    apply_out = (
        args.apply_out.resolve()
        if args.apply_out
        else qdpx_path.with_name(f"{qdpx_path.stem}-categorized.qdpx")
    )

    print("Reading QDPX...")
    codes, _ = parse_qdpx(qdpx_path, max_quotes_per_code=args.max_quotes_per_code)
    print(f"Loaded {len(codes)} codes")

    child_map = _children_map(codes)
    uncategorised = _uncategorised_codes(codes, child_map)
    parents = _parent_categories(codes, child_map)
    if not uncategorised:
        raise SystemExit("No uncategorised coded leaf codes found.")
    if not parents:
        raise SystemExit("No top-level parent categories with children found.")

    print(f"Uncategorised coded leaf codes: {len(uncategorised)}")
    print(f"Top-level parent categories: {len(parents)}")
    print("Preparing embeddings...")

    code_by_guid = {code.guid: code for code in codes}
    sim = _build_similarity(
        model_name=args.model,
        cache_dir=args.cache_dir,
        device=args.device,
        batch_size=max(1, args.embed_batch_size),
        uncategorised=uncategorised,
        parents=parents,
        child_map=child_map,
        code_by_guid=code_by_guid,
    )

    initial_state = _load_state(args.state)
    app = CategorySuggestApp(
        uncategorised=uncategorised,
        parents=parents,
        sim=sim,
        base_qdpx=qdpx_path,
        apply_out=apply_out,
        state_path=args.state,
        suggestions_csv=args.suggestions_csv,
        review_csv=args.review_csv,
        review_md=args.review_md,
        initial_state=initial_state,
        apply_on_export=args.apply_on_export,
    )
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
