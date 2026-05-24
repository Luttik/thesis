"""Remove filler-only [Me] turns and merge adjacent [Them] turns.

Processes [Me] / [Them] block-header format transcripts.

Usage:
    python remove_fillers.py "transcripts/Thesis transcript Foo.md"
    python remove_fillers.py "transcripts/Thesis transcript Foo.md" --dry-run
"""

import sys
from pathlib import Path

FILLER_WORDS = {
    "yeah", "yep", "mm-hmm", "okay", "ok", "check", "sure", "cool",
    "interesting", "ja", "oké", "sí", "ya", "yes", "no", "nee", "ajá",
    "indeed", "exactly", "great", "zeker", "duidelijk", "nice", "mm",
    "right", "mhm", "uh-huh",
}


def is_filler_only(text: str) -> bool:
    """Return True if text contains only acknowledgment words (with optional punctuation)."""
    import re
    cleaned = text.strip().lower()
    # Remove trailing/leading punctuation
    cleaned = cleaned.strip(".,!?… ")
    if not cleaned:
        return False
    # Split on spaces and commas
    parts = [p.strip().strip(".,!?") for p in re.split(r"[\s,]+", cleaned) if p.strip()]
    return bool(parts) and all(p in FILLER_WORDS for p in parts)


class Turn:
    def __init__(self, speaker: str, lines: list[str]) -> None:
        self.speaker = speaker  # "Me" or "Them"
        self.lines = lines  # Content lines (no header line)

    @property
    def content(self) -> str:
        return "\n".join(self.lines).strip()

    def is_filler(self) -> bool:
        return self.speaker == "Me" and is_filler_only(self.content)

    def render(self) -> str:
        return f"[{self.speaker}]\n" + "\n".join(self.lines)


def parse_turns(content: str) -> list[Turn]:
    """Parse transcript into a list of Turn objects."""
    turns: list[Turn] = []
    current_speaker: str | None = None
    current_lines: list[str] = []

    for line in content.split("\n"):
        stripped = line.strip()
        if stripped in ("[Me]", "[Them]"):
            if current_speaker is not None:
                # Save current turn (strip trailing blank lines)
                while current_lines and not current_lines[-1].strip():
                    current_lines.pop()
                if current_lines or current_speaker:
                    turns.append(Turn(current_speaker, current_lines))
            current_speaker = "Me" if stripped == "[Me]" else "Them"
            current_lines = []
        else:
            if current_speaker is not None:
                current_lines.append(line)

    # Save last turn
    if current_speaker is not None:
        while current_lines and not current_lines[-1].strip():
            current_lines.pop()
        turns.append(Turn(current_speaker, current_lines))

    return turns


def remove_fillers(turns: list[Turn]) -> tuple[list[Turn], int, int]:
    """Remove filler [Me] turns, merging adjacent [Them] turns."""
    removed = 0
    merged = 0
    result: list[Turn] = []

    for turn in turns:
        if turn.is_filler():
            removed += 1
            # If previous turn was [Them], flag it for potential merge with next [Them]
            if result and result[-1].speaker == "Them":
                result[-1]._pending_merge = True  # type: ignore[attr-defined]
        else:
            if (turn.speaker == "Them" and result and
                    result[-1].speaker == "Them" and
                    getattr(result[-1], "_pending_merge", False)):
                # Merge this turn into the previous [Them]
                prev = result[-1]
                prev_content = prev.content.rstrip()
                this_content = turn.content.lstrip()
                prev.lines = [(prev_content + " " + this_content).strip()]
                if hasattr(prev, "_pending_merge"):
                    del prev._pending_merge  # type: ignore[attr-defined]
                merged += 1
            else:
                if hasattr(turn, "_pending_merge"):
                    del turn._pending_merge  # type: ignore[attr-defined]
                # Clear any pending merge flag on previous turn if current is not [Them]
                if result and hasattr(result[-1], "_pending_merge"):
                    del result[-1]._pending_merge  # type: ignore[attr-defined]
                result.append(turn)

    # Clean up any remaining _pending_merge flags
    for t in result:
        if hasattr(t, "_pending_merge"):
            del t._pending_merge  # type: ignore[attr-defined]

    return result, removed, merged


def render_turns(turns: list[Turn]) -> str:
    """Render turns back to markdown string."""
    parts = [t.render() for t in turns]
    return "\n\n".join(parts) + "\n"


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python remove_fillers.py <transcript.md> [--dry-run]")
        sys.exit(1)

    path = Path(sys.argv[1])
    dry_run = "--dry-run" in sys.argv

    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    content = path.read_text(encoding="utf-8")
    turns = parse_turns(content)
    cleaned_turns, removed, merged = remove_fillers(turns)
    cleaned_content = render_turns(cleaned_turns)

    if dry_run:
        print(f"DRY RUN: would remove {removed} filler turns, merge {merged} [Them] blocks.")
        return

    path.write_text(cleaned_content, encoding="utf-8")
    print(f"Removed {removed} filler turns, merged {merged} [Them] blocks.")
    print(f"Updated {path}")


if __name__ == "__main__":
    main()
