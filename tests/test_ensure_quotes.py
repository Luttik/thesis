import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ensure_quotes import (
    LEFT_DOUBLE,
    LEFT_SINGLE,
    RIGHT_DOUBLE,
    RIGHT_SINGLE,
    find_straight_quotes,
    fix_paragraph_block,
    has_wrapping_quotes,
    is_quote_paragraph,
    is_quote_paragraph_xml,
    smarten_quotes,
    strip_wrapping_quotes,
)


class FakeParagraph:
    def __init__(self, style: str, text: str) -> None:
        self.style = type("S", (), {"name": style})()
        self.text = text


def test_smarten_nested_quotes() -> None:
    source = '"The quote that says \'internal quote\'"'
    expected = (
        f"{LEFT_DOUBLE}The quote that says {LEFT_SINGLE}internal quote{RIGHT_SINGLE}{RIGHT_DOUBLE}"
    )
    assert smarten_quotes(source) == expected


def test_smarten_contractions_are_apostrophes() -> None:
    assert smarten_quotes("it's") == f"it{RIGHT_SINGLE}s"
    assert smarten_quotes("don't") == f"don{RIGHT_SINGLE}t"
    assert smarten_quotes("they're") == f"they{RIGHT_SINGLE}re"


def test_smarten_leaves_curly_quotes_untouched() -> None:
    text = f"{LEFT_DOUBLE}already smart{RIGHT_DOUBLE}"
    assert smarten_quotes(text) == text
    assert find_straight_quotes(text) == []


def test_strip_wrapping_double_quotes() -> None:
    text = "\u201cThe whole paragraph is quoted.\u201d"
    stripped, changed = strip_wrapping_quotes(text)
    assert changed is True
    assert stripped == "The whole paragraph is quoted."


def test_keep_internal_quotes_when_unwrapping_block() -> None:
    text = (
        "\u201cThey were skeptical. \u201cOh, I need to learn a new thing.\u201d "
        "Well, if you don\u2019t adapt, you fall behind.\u201d"
    )
    stripped, changed = strip_wrapping_quotes(text)
    assert changed is True
    assert stripped.startswith("They were skeptical.")
    assert "\u201cOh, I need to learn a new thing.\u201d" in stripped


def test_only_quote_style_is_targeted() -> None:
    assert is_quote_paragraph(FakeParagraph("Quote", "x"))
    assert not is_quote_paragraph(FakeParagraph("Normal", "\u201chello\u201d"))


def test_has_wrapping_quotes_detects_outer_pair() -> None:
    assert has_wrapping_quotes("\u201chello\u201d")
    assert not has_wrapping_quotes("\u201chello")


def test_combined_paragraph_fix_applies_both_steps() -> None:
    paragraph_xml = (
        '<w:p><w:pPr><w:pStyle w:val="Quote"/></w:pPr>'
        '<w:r><w:t>"Hello there"</w:t></w:r></w:p>'
    )
    updated, smart_changed, block_changed = fix_paragraph_block(paragraph_xml)
    assert smart_changed is True
    assert block_changed is True
    assert is_quote_paragraph_xml(updated)
    assert '"Hello there"' not in updated
    assert "\u201cHello there\u201d" not in updated
    assert "Hello there" in updated
