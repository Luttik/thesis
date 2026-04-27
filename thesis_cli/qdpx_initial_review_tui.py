#!/usr/bin/env python3
"""Review initial coding suggestions from qdpx-coding quotations in a TUI.

Controls:
- a: accept
- d: decline
- e: expand span (opens exact span editor)
- r: reduce span (opens exact span editor)
- c: add/update reviewer comment
- j/k: next/previous
- z: undo
- q: save + quit
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from rich.markup import escape
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, Static

DEFAULT_WORKSPACE = Path("qdpx-coding")
DEFAULT_STATE_PATH = Path("output/qdpx-initial-review-state.json")

QUOTE_BLOCK_RE = re.compile(
    r"(?ms)^##\s+Quotation\s+(?P<number>\d+)\n(?P<body>.*?)(?=^##\s+Quotation\s+\d+\n|\Z)"
)
ID_RE = re.compile(r"<!--\s*id:\s*([A-Fa-f0-9\-]{32,36})\s*-->")
SPAN_RE = re.compile(r"<!--\s*span:\s*(\d+):(\d+)\s*-->")
CODES_RE = re.compile(r"^\*\*Codes\*\*:\s*(.*)$", re.MULTILINE)
COMMENT_RE = re.compile(r"^<!--\s*review-comment:\s*(.*?)\s*-->$", re.MULTILINE)


@dataclass
class QuoteRecord:
    file_path: Path
    file_stem: str
    quote_number: int
    guid: str
    start: int
    end: int
    codes: list[str]
    quote_markdown: str
    comment: str
    doc_text: str

    @property
    def key(self) -> str:
        return self.guid.upper()

    @property
    def selected_text(self) -> str:
        if not self.doc_text:
            stripped = []
            for line in self.quote_markdown.splitlines():
                if line.startswith("> "):
                    stripped.append(line[2:])
                elif line == ">":
                    stripped.append("")
            return "\n".join(stripped).strip()
        safe_start = max(0, min(self.start, len(self.doc_text)))
        safe_end = max(safe_start, min(self.end, len(self.doc_text)))
        return self.doc_text[safe_start:safe_end]


def _parse_codes(raw: str) -> list[str]:
    raw = raw.strip()
    if raw == "*(none)*":
        return []
    names = [c.strip() for c in re.findall(r"`([^`]+)`", raw)]
    deduped: list[str] = []
    seen: set[str] = set()
    for name in names:
        if name and name not in seen:
            deduped.append(name)
            seen.add(name)
    return deduped


def _format_codes(codes: list[str]) -> str:
    if not codes:
        return "*(none)*"
    return ", ".join(f"`{code}`" for code in codes)


def _read_document_body(document_path: Path) -> str:
    if not document_path.exists():
        return ""
    lines = document_path.read_text(encoding="utf-8").splitlines()
    start_idx = 0
    for idx, line in enumerate(lines):
        if line.startswith("<!--") or line.startswith("# "):
            continue
        if line.strip() == "":
            continue
        start_idx = idx
        break
    return "\n".join(lines[start_idx:])


def _parse_quotation_file(quote_file: Path, doc_text: str) -> tuple[str, list[QuoteRecord]]:
    text = quote_file.read_text(encoding="utf-8")
    first_match = QUOTE_BLOCK_RE.search(text)
    if first_match is None:
        return text.rstrip() + "\n", []

    header = text[: first_match.start()].rstrip() + "\n\n"
    records: list[QuoteRecord] = []

    for match in QUOTE_BLOCK_RE.finditer(text):
        quote_number = int(match.group("number"))
        body = match.group("body")

        id_match = ID_RE.search(body)
        span_match = SPAN_RE.search(body)
        codes_match = CODES_RE.search(body)
        if id_match is None or span_match is None or codes_match is None:
            continue

        guid = id_match.group(1).upper()
        start = int(span_match.group(1))
        end = int(span_match.group(2))
        codes = _parse_codes(codes_match.group(1))

        comment_match = COMMENT_RE.search(body)
        comment = comment_match.group(1).strip() if comment_match else ""

        quote_lines: list[str] = []
        for line in body.splitlines():
            if line.startswith(">"):
                quote_lines.append(line)
        quote_markdown = "\n".join(quote_lines)

        records.append(
            QuoteRecord(
                file_path=quote_file,
                file_stem=quote_file.stem,
                quote_number=quote_number,
                guid=guid,
                start=start,
                end=end,
                codes=codes,
                quote_markdown=quote_markdown,
                comment=comment,
                doc_text=doc_text,
            )
        )

    return header, records


def _write_quotation_file(header: str, records: list[QuoteRecord]) -> None:
    if not records:
        return

    lines: list[str] = [header.rstrip(), ""]
    for record in records:
        lines.append(f"## Quotation {record.quote_number}")
        lines.append(f"<!-- id: {record.guid} -->")
        lines.append(f"<!-- span: {record.start}:{record.end} -->")
        lines.append(f"**Codes**: {_format_codes(record.codes)}  ")
        if record.comment.strip():
            safe_comment = record.comment.replace("\n", " ").strip()
            lines.append(f"<!-- review-comment: {safe_comment} -->")
        lines.append("")
        if record.quote_markdown.strip():
            lines.extend(record.quote_markdown.splitlines())
        lines.append("")

    output = "\n".join(lines).rstrip() + "\n"
    records[0].file_path.write_text(output, encoding="utf-8")


def _load_quotes(workspace: Path, doc_filter: str | None, only_coded: bool) -> list[QuoteRecord]:
    quotes_dir = workspace / "quotations"
    docs_dir = workspace / "documents"
    if not quotes_dir.exists():
        raise SystemExit(f"Missing directory: {quotes_dir}")

    quote_files = sorted(quotes_dir.glob("*.md"))
    if doc_filter:
        raw = doc_filter.strip()
        path_like = Path(raw)
        needles = {
            raw.lower(),
            path_like.name.lower(),
            path_like.stem.lower(),
        }
        needles = {n for n in needles if n}
        quote_files = [
            p
            for p in quote_files
            if any(n in p.stem.lower() or n in p.name.lower() for n in needles)
        ]

    all_records: list[QuoteRecord] = []
    for quote_file in quote_files:
        doc_path = docs_dir / quote_file.name
        doc_text = _read_document_body(doc_path)
        _, records = _parse_quotation_file(quote_file, doc_text)
        for rec in records:
            if only_coded and not rec.codes:
                continue
            all_records.append(rec)
    return all_records


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"cursor": 0, "decisions": {}, "history": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(path)


class SpanEditScreen(ModalScreen[tuple[int, int] | None]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    CSS = """
    SpanEditScreen {
      align: center middle;
    }
    #span-box {
      width: 84;
      height: auto;
      border: round $primary;
      padding: 1;
      background: $surface;
    }
    """

    def __init__(self, default_start: int, default_end: int, max_len: int) -> None:
        super().__init__()
        self.default_start = default_start
        self.default_end = default_end
        self.max_len = max_len

    def compose(self) -> ComposeResult:
        yield Static(
            (
                "Edit exact span as start:end and press Enter\n"
                f"Range 0..{self.max_len}"
            ),
            id="span-box",
        )
        yield Input(value=f"{self.default_start}:{self.default_end}", id="span-input")

    def on_mount(self) -> None:
        self.query_one("#span-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        match = re.fullmatch(r"(\d+)\s*:\s*(\d+)", raw)
        if match is None:
            self.app.notify("Use format start:end", severity="warning", timeout=2)
            return
        start = int(match.group(1))
        end = int(match.group(2))
        if start < 0 or end < start or end > self.max_len:
            self.app.notify("Invalid bounds for document", severity="warning", timeout=2)
            return
        self.dismiss((start, end))

    def action_cancel(self) -> None:
        self.dismiss(None)


class CommentScreen(ModalScreen[str | None]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    CSS = """
    CommentScreen {
      align: center middle;
    }
    #comment-box {
      width: 84;
      height: auto;
      border: round $primary;
      padding: 1;
      background: $surface;
    }
    """

    def __init__(self, current_comment: str) -> None:
        super().__init__()
        self.current_comment = current_comment

    def compose(self) -> ComposeResult:
        yield Static("Reviewer comment for next AI step:", id="comment-box")
        yield Input(value=self.current_comment, id="comment-input")

    def on_mount(self) -> None:
        self.query_one("#comment-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip())

    def action_cancel(self) -> None:
        self.dismiss(None)


class InitialReviewApp(App[None]):
    BINDINGS = [
        Binding("j", "next_quote", "Next"),
        Binding("k", "prev_quote", "Prev"),
        Binding("]", "next_code", "Code+"),
        Binding("[", "prev_code", "Code-"),
        Binding("down", "next_code", "Code+"),
        Binding("up", "prev_code", "Code-"),
        Binding("space", "toggle_code", "Toggle code"),
        Binding("a", "accept", "Accept"),
        Binding("d", "decline", "Decline"),
        Binding("e", "expand", "Expand"),
        Binding("r", "reduce", "Reduce"),
        Binding("c", "comment", "Comment"),
        Binding("z", "undo", "Undo"),
        Binding("q", "quit", "Quit"),
    ]

    CSS = """
    Screen {
      layout: vertical;
    }
    #status {
      height: auto;
      border: round $accent;
      padding: 1;
      margin: 0 0 1 0;
    }
    #content {
      height: 1fr;
      border: round $primary;
      padding: 1;
    }
    """

    def __init__(
        self,
        quotes: list[QuoteRecord],
        state_path: Path,
        initial_state: dict[str, Any],
    ) -> None:
        super().__init__()
        self.quotes = quotes
        self.state_path = state_path
        self.state = initial_state
        self.cursor = int(initial_state.get("cursor", 0))
        if self.cursor >= len(quotes):
            self.cursor = max(0, len(quotes) - 1)

        raw_decisions = initial_state.get("decisions", {})
        self.decisions: dict[str, dict[str, Any]] = (
            raw_decisions if isinstance(raw_decisions, dict) else {}
        )
        raw_history = initial_state.get("history", [])
        self.history: list[dict[str, Any]] = cast(list[dict[str, Any]], raw_history)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield Static(id="status")
            yield Static(id="content")
        yield Footer()

    def on_mount(self) -> None:
        self._render()
        self._save()

    def _save(self) -> None:
        self.state["cursor"] = self.cursor
        self.state["decisions"] = self.decisions
        self.state["history"] = self.history[-1000:]
        _save_state(self.state_path, self.state)

    def _decision_for(self, quote: QuoteRecord) -> dict[str, Any]:
        return cast(dict[str, Any], self.decisions.get(quote.key, {}))

    def _decision_status(self, quote: QuoteRecord) -> str:
        d = self._decision_for(quote)
        return str(d.get("status", "pending"))

    def _reviewed_count(self) -> int:
        reviewed = 0
        for q in self.quotes:
            if self._decision_status(q) in {"accepted", "declined"}:
                reviewed += 1
        return reviewed

    def _effective_codes(self, quote: QuoteRecord) -> list[str]:
        d = self._decision_for(quote)
        raw_excluded = d.get("excluded_codes")
        if isinstance(raw_excluded, list):
            excluded = {str(c) for c in raw_excluded}
            return [c for c in quote.codes if c not in excluded]
        raw = d.get("codes")
        if isinstance(raw, list):
            return [str(c) for c in raw]
        return list(quote.codes)

    def _all_codes(self, quote: QuoteRecord) -> list[str]:
        return list(quote.codes)

    def _excluded_codes(self, quote: QuoteRecord) -> set[str]:
        d = self._decision_for(quote)
        raw = d.get("excluded_codes")
        if isinstance(raw, list):
            return {str(c) for c in raw}
        return set()

    def _current_span(self, quote: QuoteRecord) -> tuple[int, int]:
        d = self._decision_for(quote)
        start = int(d.get("start", quote.start))
        end = int(d.get("end", quote.end))
        if quote.doc_text:
            max_len = len(quote.doc_text)
            start = max(0, min(start, max_len))
            end = max(start, min(end, max_len))
        return start, end

    def _code_cursor(self, quote: QuoteRecord, code_count: int) -> int:
        d = self._decision_for(quote)
        idx = int(d.get("code_cursor", 0))
        if code_count <= 0:
            return 0
        return max(0, min(idx, code_count - 1))

    def _set_code_cursor(self, quote: QuoteRecord, idx: int) -> None:
        self._apply_decision({"code_cursor": idx}, auto_advance=False)

    def _selected_text_preview(self, quote: QuoteRecord, width: int = 1200) -> str:
        start, end = self._current_span(quote)
        if quote.doc_text:
            txt = quote.doc_text[start:end].strip()
        else:
            txt = quote.selected_text.strip()
        if not txt:
            return "(no selected text available)"
        txt = re.sub(r"\s+", " ", txt)
        if len(txt) > width:
            return txt[: width - 3].rstrip() + "..."
        return txt

    def _quote_snippet(self, quote: QuoteRecord) -> str:
        lines: list[str] = []
        for line in quote.quote_markdown.splitlines():
            if line.startswith("> "):
                lines.append(line[2:])
            elif line.startswith(">"):
                lines.append(line[1:])
        raw = " ".join(lines).strip()
        raw = re.sub(r"\s+", " ", raw)
        return raw

    def _fallback_span_by_snippet(self, quote: QuoteRecord) -> tuple[int, int] | None:
        if not quote.doc_text:
            return None
        snippet = self._quote_snippet(quote)
        if not snippet:
            return None
        parts = [p.strip() for p in re.split(r"\.\.\.|…", snippet) if p.strip()]
        parts.sort(key=len, reverse=True)
        doc_lower = quote.doc_text.lower()
        for part in parts:
            norm = re.sub(r"\s+", " ", part).strip()
            if len(norm) < 14:
                continue
            idx = doc_lower.find(norm.lower())
            if idx != -1:
                return idx, idx + len(norm)

        token_source = re.sub(r"[^\w\s]", " ", snippet.lower())
        tokens = [t for t in token_source.split() if len(t) >= 4]
        if not tokens:
            return None

        best_score = 0
        best_span: tuple[int, int] | None = None
        cursor = 0
        for line in quote.doc_text.splitlines(keepends=True):
            clean_line = re.sub(r"[^\w\s]", " ", line.lower())
            score = sum(1 for t in tokens if t in clean_line)
            if score > best_score:
                start = cursor
                end = cursor + len(line.rstrip("\n"))
                best_span = (start, end)
                best_score = score
            cursor += len(line)

        if best_span is not None and best_score >= 2:
            return best_span
        return None

    def _paragraph_context(self, quote: QuoteRecord) -> tuple[str, str, str, tuple[int, int] | None]:
        if not quote.doc_text:
            return "", "", "", None

        start, end = self._current_span(quote)
        if end - start <= 1:
            fallback = self._fallback_span_by_snippet(quote)
            if fallback is not None:
                start, end = fallback
            else:
                return "", "", "", None

        doc = quote.doc_text
        line_start = doc.rfind("\n", 0, start)
        line_start = 0 if line_start < 0 else line_start + 1
        line_end = doc.find("\n", end)
        line_end = len(doc) if line_end < 0 else line_end

        prev_end = max(0, line_start - 1)
        prev_start = doc.rfind("\n", 0, prev_end)
        prev_start = 0 if prev_start < 0 else prev_start + 1
        prev_para = doc[prev_start:prev_end].strip() if prev_end > 0 else ""

        next_start = min(len(doc), line_end + 1)
        next_end = doc.find("\n", next_start)
        next_end = len(doc) if next_end < 0 else next_end
        next_para = doc[next_start:next_end].strip() if next_start < len(doc) else ""

        curr_para = doc[line_start:line_end]
        rel_s = max(0, start - line_start)
        rel_e = max(rel_s, min(len(curr_para), end - line_start))
        if rel_e <= rel_s:
            rel_s = 0
            rel_e = len(curr_para)
        return prev_para, curr_para, next_para, (rel_s, rel_e)

    def _render_codes_panel(self, quote: QuoteRecord) -> str:
        all_codes = self._all_codes(quote)
        if not all_codes:
            return "[bold cyan]Codes[/bold cyan] *(none)*"

        excluded = self._excluded_codes(quote)
        idx = self._code_cursor(quote, len(all_codes))
        lines = ["[bold cyan]Codes[/bold cyan] (click code, or use bracket keys plus space)"]
        for i, code in enumerate(all_codes):
            pointer = "->" if i == idx else "  "
            mark = "off" if code in excluded else "on"
            lines.append(
                f"{pointer} [@click=toggle_code_at({i})]({mark}) {escape(code)}[/]"
            )
        return "\n".join(lines)

    def _render_context_panel(self, quote: QuoteRecord) -> str:
        prev_para, curr_para, next_para, rel = self._paragraph_context(quote)
        start, end = self._current_span(quote)
        controls = (
            "[bold cyan]Span controls[/bold cyan] "
            "[@click=span_start_left(10)]S-10[/] "
            "[@click=span_start_left(1)]S-1[/] "
            "[@click=span_start_right(1)]S+1[/] "
            "[@click=span_start_right(10)]S+10[/]  "
            "[@click=span_end_left(10)]E-10[/] "
            "[@click=span_end_left(1)]E-1[/] "
            "[@click=span_end_right(1)]E+1[/] "
            "[@click=span_end_right(10)]E+10[/] "
            f"[dim](start:end = {start}:{end})[/dim]"
        )
        if rel is None or not curr_para:
            snippet = self._quote_snippet(quote)
            if not snippet:
                snippet = self._selected_text_preview(quote)
            return (
                f"{controls}\n\n"
                "[bold cyan]Context[/bold cyan]\n"
                "(document context unavailable; showing quoted text)\n\n"
                f"{escape(snippet)}"
            )

        rs, re_ = rel
        before = escape(curr_para[:rs])
        mid = escape(curr_para[rs:re_])
        after = escape(curr_para[re_:])
        if not mid:
            mid = escape(curr_para)
            before = ""
            after = ""
        current_marked = f"{before}[bold black on green]{mid}[/]{after}"

        out = [
            controls,
            "",
            "[bold cyan]Context (paragraph before / selected paragraph / paragraph after)[/bold cyan]",
        ]
        out.append("")
        out.append("[dim]Before[/dim]")
        out.append(escape(prev_para) if prev_para else "[dim](none)[/dim]")
        out.append("")
        out.append("[bold]Current (selected span highlighted)[/bold]")
        out.append(current_marked)
        out.append("")
        out.append("[dim]After[/dim]")
        out.append(escape(next_para) if next_para else "[dim](none)[/dim]")
        return "\n".join(out)

    def _render(self) -> None:
        status = self.query_one("#status", Static)
        content = self.query_one("#content", Static)
        if not self.quotes:
            status.update("No quotations found for review.")
            content.update("")
            return

        q = self.quotes[self.cursor]
        d = self._decision_for(q)
        reviewed_count = self._reviewed_count()
        codes = self._effective_codes(q)
        status_text = (
            f"Quote {self.cursor + 1}/{len(self.quotes)} | "
            f"Reviewed {reviewed_count}/{len(self.quotes)}\n"
            f"Doc {q.file_stem} | Quotation #{q.quote_number}\n"
            f"Decision {self._decision_status(q)} | Span {self._current_span(q)[0]}:{self._current_span(q)[1]} | Codes {len(codes)}"
        )
        status.update(status_text)

        comment = str(d.get("comment", "") or q.comment)
        lines = [self._render_codes_panel(q), "", self._render_context_panel(q)]
        if comment.strip():
            lines.extend(
                ["", "[bold yellow]Reviewer comment[/bold yellow]", escape(comment.strip())]
            )
        content.update("\n".join(lines))

    def _apply_decision(self, patch: dict[str, Any], auto_advance: bool = True) -> None:
        if not self.quotes:
            return
        q = self.quotes[self.cursor]
        key = q.key
        previous = self.decisions.get(key)
        self.history.append({"cursor": self.cursor, "key": key, "previous": previous})

        merged = dict(previous) if isinstance(previous, dict) else {}
        merged.update(patch)
        self.decisions[key] = merged

        if auto_advance and self.cursor < len(self.quotes) - 1:
            self.cursor += 1
        self._render()
        self._save()

    def action_next_quote(self) -> None:
        if not self.quotes:
            return
        self.cursor = min(self.cursor + 1, len(self.quotes) - 1)
        self._render()
        self._save()

    def action_prev_quote(self) -> None:
        if not self.quotes:
            return
        self.cursor = max(self.cursor - 1, 0)
        self._render()
        self._save()

    def action_accept(self) -> None:
        self._apply_decision({"status": "accepted"})

    def action_decline(self) -> None:
        self._apply_decision({"status": "declined"})

    def action_next_code(self) -> None:
        if not self.quotes:
            return
        q = self.quotes[self.cursor]
        codes = self._all_codes(q)
        if not codes:
            return
        idx = self._code_cursor(q, len(codes))
        self._set_code_cursor(q, min(idx + 1, len(codes) - 1))

    def action_prev_code(self) -> None:
        if not self.quotes:
            return
        q = self.quotes[self.cursor]
        codes = self._all_codes(q)
        if not codes:
            return
        idx = self._code_cursor(q, len(codes))
        self._set_code_cursor(q, max(0, idx - 1))

    def action_toggle_code(self) -> None:
        if not self.quotes:
            return
        q = self.quotes[self.cursor]
        all_codes = self._all_codes(q)
        if not all_codes:
            return
        idx = self._code_cursor(q, len(all_codes))
        target = all_codes[idx]
        excluded = self._excluded_codes(q)
        if target in excluded:
            excluded.remove(target)
        else:
            excluded.add(target)
        effective = [c for c in all_codes if c not in excluded]
        self._apply_decision(
            {
                "status": "accepted",
                "excluded_codes": sorted(excluded),
                "codes": effective,
                "code_cursor": idx,
            },
            auto_advance=False,
        )

    def action_toggle_code_at(self, idx: int) -> None:
        if not self.quotes:
            return
        q = self.quotes[self.cursor]
        all_codes = self._all_codes(q)
        if not all_codes:
            return
        if idx < 0 or idx >= len(all_codes):
            return
        self._set_code_cursor(q, idx)
        self.action_toggle_code()

    def _nudge_span(self, delta_start: int = 0, delta_end: int = 0) -> None:
        if not self.quotes:
            return
        q = self.quotes[self.cursor]
        start, end = self._current_span(q)
        new_start = start + delta_start
        new_end = end + delta_end

        max_len = len(q.doc_text) if q.doc_text else max(end, 1)
        new_start = max(0, min(new_start, max_len))
        new_end = max(0, min(new_end, max_len))
        if new_end < new_start:
            new_end = new_start
        if new_end == new_start:
            new_end = min(max_len, new_start + 1)

        self._apply_decision(
            {"status": "accepted", "start": new_start, "end": new_end},
            auto_advance=False,
        )

    def action_span_start_left(self, step: int = 1) -> None:
        self._nudge_span(delta_start=-abs(int(step)))

    def action_span_start_right(self, step: int = 1) -> None:
        self._nudge_span(delta_start=abs(int(step)))

    def action_span_end_left(self, step: int = 1) -> None:
        self._nudge_span(delta_end=-abs(int(step)))

    def action_span_end_right(self, step: int = 1) -> None:
        self._nudge_span(delta_end=abs(int(step)))

    def _span_editor(self, default_start: int, default_end: int) -> None:
        if not self.quotes:
            return
        q = self.quotes[self.cursor]
        max_len = len(q.doc_text) if q.doc_text else max(q.end, default_end)
        self.push_screen(
            SpanEditScreen(default_start=default_start, default_end=default_end, max_len=max_len),
            callback=self._apply_span,
        )

    def action_expand(self) -> None:
        if not self.quotes:
            return
        q = self.quotes[self.cursor]
        max_len = len(q.doc_text) if q.doc_text else q.end + 100
        default_start = max(0, q.start - 40)
        default_end = min(max_len, q.end + 40)
        self._span_editor(default_start, default_end)

    def action_reduce(self) -> None:
        if not self.quotes:
            return
        q = self.quotes[self.cursor]
        span = max(1, q.end - q.start)
        step = max(1, min(20, span // 2))
        default_start = min(q.end - 1, q.start + step)
        default_end = max(default_start + 1, q.end - step)
        self._span_editor(default_start, default_end)

    def _apply_span(self, value: tuple[int, int] | None) -> None:
        if value is None:
            return
        start, end = value
        self._apply_decision({"status": "accepted", "start": start, "end": end})

    def action_comment(self) -> None:
        if not self.quotes:
            return
        q = self.quotes[self.cursor]
        current = str(self._decision_for(q).get("comment", q.comment))
        self.push_screen(CommentScreen(current_comment=current), callback=self._apply_comment)

    def _apply_comment(self, value: str | None) -> None:
        if value is None:
            return
        self._apply_decision({"comment": value}, auto_advance=False)

    def action_undo(self) -> None:
        if not self.history:
            return
        entry = self.history.pop()
        cursor = int(entry.get("cursor", 0))
        key = str(entry.get("key", ""))
        previous = entry.get("previous")
        if isinstance(previous, dict):
            self.decisions[key] = previous
        else:
            self.decisions.pop(key, None)
        if self.quotes:
            self.cursor = max(0, min(cursor, len(self.quotes) - 1))
        self._render()
        self._save()

    async def action_quit(self) -> None:
        self._save()
        self.exit()


def _apply_decisions_to_workspace(
    quotes: list[QuoteRecord], decisions: dict[str, dict[str, Any]]
) -> None:
    if not quotes:
        return

    grouped: dict[Path, list[QuoteRecord]] = {}
    for quote in quotes:
        grouped.setdefault(quote.file_path, []).append(quote)

    for quote_file, records in grouped.items():
        doc_path = quote_file.parent.parent / "documents" / quote_file.name
        doc_text = _read_document_body(doc_path)
        header, file_records = _parse_quotation_file(quote_file, doc_text)
        by_guid = {r.guid.upper(): r for r in file_records}

        for guid, decision in decisions.items():
            target = by_guid.get(guid.upper())
            if target is None:
                continue
            status = str(decision.get("status", "pending"))
            if status == "declined":
                target.codes = []
            if status == "accepted" and "codes" in decision:
                raw_codes = decision.get("codes")
                if isinstance(raw_codes, list):
                    target.codes = [str(c) for c in raw_codes]
            if status in {"accepted", "declined"}:
                if "start" in decision and "end" in decision:
                    start = int(decision["start"])
                    end = int(decision["end"])
                    if target.doc_text:
                        max_len = len(target.doc_text)
                        start = max(0, min(start, max_len))
                        end = max(start, min(end, max_len))
                    target.start = start
                    target.end = end
            if "comment" in decision:
                target.comment = str(decision.get("comment", "")).strip()

        _write_quotation_file(header, file_records)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Review initial coding suggestions from qdpx-coding."
    )
    parser.add_argument(
        "--qdpx",
        type=Path,
        default=None,
        help="Optional .qdpx path used to auto-import if workspace is missing",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=DEFAULT_WORKSPACE,
        help="Path to qdpx-coding workspace (default: qdpx-coding)",
    )
    parser.add_argument(
        "--doc",
        type=str,
        default=None,
        help="Filter document by filename substring (case-insensitive)",
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=DEFAULT_STATE_PATH,
        help="State file for autosave/resume",
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Resume from existing state",
    )
    parser.add_argument(
        "--only-coded",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Only include quotations with at least one code",
    )
    return parser.parse_args()


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


def _ensure_workspace_exists(workspace: Path, qdpx_override: Path | None) -> None:
    if workspace.exists():
        return

    workspace_root = Path(__file__).resolve().parent.parent
    qdpx_path = qdpx_override.resolve() if qdpx_override else None
    if qdpx_path is None:
        candidates = _find_qdpx_candidates(workspace_root)
        qdpx_path = candidates[0].resolve() if candidates else None

    if qdpx_path is None or not qdpx_path.exists():
        raise SystemExit(
            f"Workspace not found: {workspace}\n"
            "No .qdpx file found to auto-import. Run qdpx_import first or pass --qdpx."
        )

    import_script = workspace_root / ".cursor" / "skills" / "qdpx" / "qdpx_import.py"
    if not import_script.exists():
        raise SystemExit(
            f"Workspace not found: {workspace}\n"
            f"Import script missing: {import_script}"
        )

    cmd = [
        sys.executable,
        str(import_script),
        "--qdpx",
        str(qdpx_path),
        "--out",
        str(workspace),
    ]
    print(f"Workspace missing. Importing from {qdpx_path} to {workspace}...")
    result = subprocess.run(cmd, cwd=workspace_root, check=False)
    if result.returncode != 0 or not workspace.exists():
        retry_cmd = (
            "python .cursor/skills/qdpx/qdpx_import.py "
            f"--qdpx \"{qdpx_path}\" --out \"{workspace}\""
        )
        raise SystemExit(
            "Auto-import failed. Run qdpx import manually, then retry:\n"
            f"{retry_cmd}"
        )


def main() -> int:
    args = parse_args()
    workspace = args.workspace.resolve()
    _ensure_workspace_exists(workspace, args.qdpx)

    quotes = _load_quotes(workspace=workspace, doc_filter=args.doc, only_coded=args.only_coded)
    if not quotes:
        print("No quotations matched filters. Nothing to review.")
        return 0

    state_path = args.state.resolve()
    state = (
        _load_state(state_path)
        if args.resume
        else {"cursor": 0, "decisions": {}, "history": []}
    )
    app = InitialReviewApp(quotes=quotes, state_path=state_path, initial_state=state)
    app.run()

    final_state = _load_state(state_path)
    raw_decisions = final_state.get("decisions", {})
    decisions = cast(
        dict[str, dict[str, Any]],
        raw_decisions if isinstance(raw_decisions, dict) else {},
    )
    _apply_decisions_to_workspace(quotes, decisions)

    reviewed = 0
    for decision in decisions.values():
        if str(decision.get("status", "pending")) in {"accepted", "declined"}:
            reviewed += 1
    print(f"Applied review decisions to qdpx-coding quotations: {reviewed} reviewed entries")
    print(f"State: {state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
