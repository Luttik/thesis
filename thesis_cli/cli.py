"""Poetry console entrypoints for QDPX dedupe tooling."""

from __future__ import annotations

from thesis_cli.launch_qdpx_dedupe_tui import main as launch_main
from thesis_cli.qdpx_category_suggest_tui import main as category_suggest_main
from thesis_cli.qdpx_code_search_tui import main as code_search_main
from thesis_cli.qdpx_dedupe_apply import main as dedupe_apply_main
from thesis_cli.qdpx_dedupe_tui import main as dedupe_main
from thesis_cli.qdpx_initial_review_tui import main as initial_review_main
from thesis_cli.qdpx_paragraph_vast import main as paragraph_vast_main


def qdpx_dedupe() -> int:
    """Run the QDPX dedupe TUI command."""
    return dedupe_main()


def qdpx_dedupe_launch() -> int:
    """Run the launcher that opens dedupe TUI in new terminal window."""
    return launch_main()


def qdpx_code_search() -> int:
    """Run the code search TUI for finding existing codes by similarity."""
    return code_search_main()


def qdpx_dedupe_apply() -> int:
    """Apply dedupe decisions back into a new QDPX file."""
    return dedupe_apply_main()


def qdpx_initial_review() -> int:
    """Run the initial-coding review TUI for quotations."""
    return initial_review_main()


def qdpx_category_suggest() -> int:
    """Run category suggestion TUI for uncategorised codes."""
    return category_suggest_main()


def qdpx_paragraph_vast() -> int:
    """Run paragraph-level local vector search for QDPX documents."""
    return paragraph_vast_main()


def qdpx_code_search_test() -> int:
    """Run the focused pytest suite for code-search behavior."""
    from pytest import main as pytest_main

    return pytest_main(["tests/test_qdpx_code_search_tui.py"])
