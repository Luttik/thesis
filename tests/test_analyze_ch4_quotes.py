import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.analyze_ch4_quotes import (
    QuoteWordCount,
    build_section_reports,
    count_words,
    find_inline_quote_ranges,
    paragraph_quote_counts,
)


def test_count_words_basic() -> None:
    assert count_words("One two three.") == 3


def test_inline_quote_ranges() -> None:
    text = "She said \u201chello world\u201d and left."
    ranges = find_inline_quote_ranges(text)
    assert ranges == [(len("She said \u201c"), len("She said \u201chello world"))]


def test_quote_paragraph_style_counts_all_words() -> None:
    class FakeStyle:
        name = "Quote"

    class FakeParagraph:
        style = FakeStyle()
        text = "This entire block is quoted."

    counts = paragraph_quote_counts(FakeParagraph())
    assert counts.total_words == 5
    assert counts.quoted_words == 5
    assert counts.outside_words == 0


def test_mixed_inline_and_outside_words() -> None:
    text = (
        "Interviewee 9 noted \u201ctalk to your peers at conferences\u201d "
        "as important leadership practice."
    )
    counts = paragraph_quote_counts(type("P", (), {"style": None, "text": text})())
    assert counts.total_words == 13
    assert counts.quoted_words == 6
    assert round(counts.quoted_pct, 1) == 46.2


def test_chapter_total_percentages() -> None:
    counts = QuoteWordCount(total_words=100, quoted_words=25)
    assert counts.outside_words == 75
    assert counts.quoted_pct == 25.0
    assert counts.outside_pct == 75.0
