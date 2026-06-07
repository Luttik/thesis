import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.count_participant_quotes import (
    attribution_interviewee,
    continues_quote_intro,
    count_participant_quotes,
    display_name,
    find_inline_quote_ranges,
    interviewee_before,
    looks_like_analysis,
)


class FakeParagraph:
    def __init__(self, style: str, text: str) -> None:
        self.style = type("S", (), {"name": style})()
        self.text = text


def test_attribution_line() -> None:
    assert attribution_interviewee("\u2014 Interviewee 13") == 13


def test_intro_colon_continuation() -> None:
    intro = "As interviewee 4 noted:"
    assert continues_quote_intro(intro) == 4
    assert not looks_like_analysis(
        "It goes so fast that they get overwhelmed."
    )


def test_inline_quote_uses_interviewee_before_quote() -> None:
    text = "Interviewee 12 was direct: \u201cYou have to act.\u201d"
    start, _ = find_inline_quote_ranges(text)[0]
    assert interviewee_before(text, start) == 12


def test_display_name_falls_back_to_blank() -> None:
    assert display_name(99, {1: "Andreea Bulisache"}) == ""


def test_display_name_uses_mapping() -> None:
    assert display_name(12, {12: "Scott Brinker"}) == "Scott Brinker"


def test_count_block_and_inline_quotes() -> None:
    paragraphs = [
        FakeParagraph("Normal", "Interviewee 6 noted:"),
        FakeParagraph("Normal", "We should move faster on this."),
        FakeParagraph("Normal", "Interviewee 8 said \u201chello\u201d here."),
        FakeParagraph("Quote", "Block quote text."),
        FakeParagraph("Normal", "\u2014 Interviewee 8"),
    ]
    counts, notes = count_participant_quotes(paragraphs)
    assert counts[6] == 1
    assert counts[8] == 2
    assert notes == []
