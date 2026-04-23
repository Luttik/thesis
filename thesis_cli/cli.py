"""Poetry console entrypoints for QDPX dedupe tooling."""

from __future__ import annotations

from thesis_cli.launch_qdpx_dedupe_tui import main as launch_main
from thesis_cli.qdpx_dedupe_tui import main as dedupe_main


def qdpx_dedupe() -> int:
    """Run the QDPX dedupe TUI command."""
    return dedupe_main()


def qdpx_dedupe_launch() -> int:
    """Run the launcher that opens dedupe TUI in new terminal window."""
    return launch_main()
