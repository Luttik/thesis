"""Analyse quotation density by section in Chapter 4 of the thesis docx."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import typer
from docx import Document
from docx.text.paragraph import Paragraph

app = typer.Typer(add_completion=False, no_args_is_help=True)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOCX = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"

OPEN_DOUBLE = {'"', "\u201c"}
CLOSE_DOUBLE = {'"', "\u201d"}
QUOTE_STYLES = {"Quote", "Block Text"}

WORD_RE = re.compile(r"[\w\u2019'-]+", re.UNICODE)
SECTION_RE = re.compile(r"^(?P<id>\d+(?:\.\d+)*)\s*[\t ]+(?P<title>.+)$")


@dataclass
class QuoteWordCount:
    total_words: int = 0
    quoted_words: int = 0

    @property
    def outside_words(self) -> int:
        return self.total_words - self.quoted_words

    @property
    def quoted_pct(self) -> float:
        if self.total_words == 0:
            return 0.0
        return 100.0 * self.quoted_words / self.total_words

    @property
    def outside_pct(self) -> float:
        return 100.0 - self.quoted_pct

    def add(self, other: QuoteWordCount) -> None:
        self.total_words += other.total_words
        self.quoted_words += other.quoted_words


@dataclass
class SectionReport:
    section_id: str
    title: str
    heading_level: int
    counts: QuoteWordCount
    quote_paragraphs: int = 0
    inline_quote_spans: int = 0


def count_words(text: str) -> int:
    return sum(1 for token in WORD_RE.findall(text) if re.search(r"\w", token, re.UNICODE))


def find_inline_quote_ranges(text: str) -> list[tuple[int, int]]:
    """Return character ranges (start, end) of text inside double quotation marks."""
    ranges: list[tuple[int, int]] = []
    inside = False
    start = 0

    for index, char in enumerate(text):
        if char in OPEN_DOUBLE and not inside:
            inside = True
            start = index + 1
            continue

        if char in CLOSE_DOUBLE and inside:
            if index > start:
                ranges.append((start, index))
            inside = False

    return ranges


def paragraph_quote_counts(paragraph: Paragraph) -> QuoteWordCount:
    text = paragraph.text.strip()
    if not text:
        return QuoteWordCount()

    style = paragraph.style.name if paragraph.style else "Normal"
    if style in QUOTE_STYLES:
        words = count_words(text)
        return QuoteWordCount(total_words=words, quoted_words=words)

    ranges = find_inline_quote_ranges(text)
    quoted_text = " ".join(text[start:end] for start, end in ranges)
    quoted_words = count_words(quoted_text)
    total_words = count_words(text)
    return QuoteWordCount(total_words=total_words, quoted_words=quoted_words)


def paragraph_quote_spans(paragraph: Paragraph) -> tuple[int, int]:
    style = paragraph.style.name if paragraph.style else "Normal"
    if style in QUOTE_STYLES:
        return (1, 0)
    ranges = find_inline_quote_ranges(paragraph.text)
    return (0, len(ranges))


def heading_level(paragraph: Paragraph) -> int | None:
    style = paragraph.style.name if paragraph.style else ""
    match = re.match(r"Heading\s+(\d+)", style)
    if not match:
        return None
    return int(match.group(1))


def parse_section_heading(text: str) -> tuple[str, str] | None:
    match = SECTION_RE.match(text.strip())
    if not match:
        return None
    return match.group("id"), match.group("title").strip()


def is_chapter_four_start(paragraph: Paragraph) -> bool:
    text = paragraph.text.strip()
    if not text.startswith("4."):
        return False
    if heading_level(paragraph) != 1:
        return False
    return "Findings" in text


def is_chapter_five_start(paragraph: Paragraph) -> bool:
    text = paragraph.text.strip()
    return text.startswith("5.") and heading_level(paragraph) == 1


def iter_chapter_four_paragraphs(doc: Document) -> list[Paragraph]:
    paragraphs = doc.paragraphs
    start_index = next(
        (index for index, paragraph in enumerate(paragraphs) if is_chapter_four_start(paragraph)),
        None,
    )
    if start_index is None:
        raise ValueError("Chapter 4 heading not found (expected Heading 1: '4. Findings').")

    end_index = next(
        (
            index
            for index, paragraph in enumerate(paragraphs[start_index + 1 :], start=start_index + 1)
            if is_chapter_five_start(paragraph)
        ),
        len(paragraphs),
    )
    return paragraphs[start_index:end_index]


def build_section_reports(
    paragraphs: list[Paragraph],
    *,
    include_subsections: bool,
) -> list[SectionReport]:
    reports: dict[str, SectionReport] = {}
    current_section_id = "4"
    current_title = "Findings (chapter intro)"
    current_level = 1

    def ensure_section(section_id: str, title: str, level: int) -> SectionReport:
        if section_id not in reports:
            reports[section_id] = SectionReport(
                section_id=section_id,
                title=title,
                heading_level=level,
                counts=QuoteWordCount(),
            )
        return reports[section_id]

    ensure_section(current_section_id, current_title, current_level)

    for paragraph in paragraphs:
        level = heading_level(paragraph)
        parsed = parse_section_heading(paragraph.text) if level else None

        if parsed and level is not None:
            section_id, title = parsed
            if not section_id.startswith("4."):
                continue

            current_section_id = section_id
            current_title = title
            current_level = level

            if include_subsections or level <= 2:
                ensure_section(section_id, title, level)
            continue

        counts = paragraph_quote_counts(paragraph)
        quote_paragraphs, inline_spans = paragraph_quote_spans(paragraph)
        if counts.total_words == 0:
            continue

        targets: set[str] = {"4"}
        parts = current_section_id.split(".")
        for index in range(2, len(parts) + 1):
            candidate = ".".join(parts[:index])
            report = reports.get(candidate)
            if report is None:
                continue
            if include_subsections or report.heading_level <= 2:
                targets.add(candidate)

        if include_subsections:
            targets.add(current_section_id)
            ensure_section(current_section_id, current_title, current_level)
        elif current_level <= 2:
            targets.add(current_section_id)
            ensure_section(current_section_id, current_title, current_level)

        for target_id in targets:
            report = ensure_section(
                target_id,
                reports[target_id].title if target_id in reports else current_title,
                reports[target_id].heading_level if target_id in reports else current_level,
            )
            report.counts.add(counts)
            report.quote_paragraphs += quote_paragraphs
            report.inline_quote_spans += inline_spans

    def sort_key(section_id: str) -> tuple[int, ...]:
        return tuple(int(part) for part in section_id.split("."))

    visible = [
        report
        for report in reports.values()
        if include_subsections or report.heading_level <= 2 or report.section_id == "4"
    ]
    return sorted(visible, key=lambda report: sort_key(report.section_id))


def format_report(reports: list[SectionReport]) -> str:
    lines = [
        "Chapter 4 quotation word analysis",
        "",
        f"{'Section':<10} {'Words':>7} {'In quotes':>10} {'Outside':>10} "
        f"{'Quoted %':>9} {'Outside %':>10}  Title",
        "-" * 95,
    ]

    for report in reports:
        lines.append(
            f"{report.section_id:<10} "
            f"{report.counts.total_words:>7,} "
            f"{report.counts.quoted_words:>10,} "
            f"{report.counts.outside_words:>10,} "
            f"{report.counts.quoted_pct:>8.1f}% "
            f"{report.counts.outside_pct:>9.1f}%  "
            f"{report.title}"
        )

    chapter_total = QuoteWordCount()
    for report in reports:
        if report.section_id == "4":
            chapter_total = report.counts
            break

    lines.extend(
        [
            "-" * 95,
            f"{'TOTAL':<10} "
            f"{chapter_total.total_words:>7,} "
            f"{chapter_total.quoted_words:>10,} "
            f"{chapter_total.outside_words:>10,} "
            f"{chapter_total.quoted_pct:>8.1f}% "
            f"{chapter_total.outside_pct:>9.1f}%",
        ]
    )
    return "\n".join(lines)


@app.command()
def analyze(
    input_path: Path = typer.Argument(
        None,
        help="Thesis docx to analyse. Defaults to the main thesis draft.",
    ),
    subsections: bool = typer.Option(
        False,
        "--subsections",
        help="Include Heading 3 and Heading 4 subsections (e.g. 4.1.1, 4.3.1).",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print machine-readable JSON instead of a table.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional path to write the report text or JSON.",
    ),
) -> None:
    """Report quoted vs non-quoted word counts for Chapter 4 sections."""
    path = input_path or DEFAULT_DOCX
    if not path.exists():
        typer.echo(f"File not found: {path}", err=True)
        raise typer.Exit(code=1)

    doc = Document(str(path))
    paragraphs = iter_chapter_four_paragraphs(doc)
    reports = build_section_reports(paragraphs, include_subsections=subsections)

    if json_output:
        payload = [
            {
                **asdict(report),
                "counts": asdict(report.counts),
                "quoted_pct": round(report.counts.quoted_pct, 2),
                "outside_pct": round(report.counts.outside_pct, 2),
            }
            for report in reports
        ]
        rendered = json.dumps(payload, indent=2)
    else:
        rendered = format_report(reports)

    typer.echo(rendered)

    if output:
        output.write_text(rendered + "\n", encoding="utf-8")
        typer.echo(f"Wrote {output}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
