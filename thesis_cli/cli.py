"""Poetry console entrypoints for QDPX dedupe tooling."""

from __future__ import annotations

from collections.abc import Callable

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


def tools_menu() -> int:
    """Show a numbered tool list and launch selection."""
    tools: list[tuple[str, Callable[[], int]]] = [
        ("Dedupe review launcher", qdpx_dedupe_launch),
        ("Dedupe review TUI", qdpx_dedupe),
        ("Code search TUI", qdpx_code_search),
        ("Paragraph VAST", qdpx_paragraph_vast),
        ("Category suggest TUI", qdpx_category_suggest),
        ("Dedupe apply", qdpx_dedupe_apply),
        ("Initial coding review TUI", qdpx_initial_review),
        ("Code search tests", qdpx_code_search_test),
    ]

    print("Select a tool:")
    for index, (label, _) in enumerate(tools, start=1):
        print(f"{index}. {label}")

    try:
        choice = input("Enter number: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return 1

    if not choice.isdigit():
        print("Invalid selection.")
        return 1

    selected = int(choice)
    if selected < 1 or selected > len(tools):
        print("Selection out of range.")
        return 1

    _, selected_tool = tools[selected - 1]
    return selected_tool()


def dedupe() -> int:
    return qdpx_dedupe()


def dedupe_launch() -> int:
    return qdpx_dedupe_launch()


def code_search() -> int:
    return qdpx_code_search()


def dedupe_apply() -> int:
    return qdpx_dedupe_apply()


def initial_review() -> int:
    return qdpx_initial_review()


def category_suggest() -> int:
    return qdpx_category_suggest()


def paragraph_vast() -> int:
    return qdpx_paragraph_vast()


def code_search_test() -> int:
    return qdpx_code_search_test()
