"""Clean a [Me]/[Them] section-header transcript.

Rules applied:
- Remove [Me] turns that contain only filler/acknowledgement words.
- Merge consecutive same-speaker turns (no other speaker between them).
- Apply targeted text fixes (stutters, ASR errors).
"""
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Filler detection
# ---------------------------------------------------------------------------

FILLER_WORDS = {
    # English
    "yeah", "yep", "yup", "mm-hmm", "mm", "mhm", "hmm", "hm",
    "okay", "ok", "check", "sure", "cool", "interesting", "oh",
    "right", "uh-huh", "uhm", "um", "uh", "good", "so", "wow",
    "indeed", "exactly", "great",
    # Dutch / Spanish
    "ja", "oké", "oke", "ya", "yes", "no", "nee", "aja", "ajá",
    "zeker", "duidelijk",
}


def is_filler_only(content: str) -> bool:
    """Return True if a [Me] turn contains only filler words/sounds/annotations."""
    # Remove action annotations like [laughs], [lacht], [zingt]
    cleaned = re.sub(r"\[[\w\s]+\]", "", content).strip()
    if not cleaned:
        return True  # empty after removing annotations → filler
    # Tokenise by whitespace and punctuation (including hyphens)
    tokens = re.split(r"[\s,.\-!?;:]+", cleaned.lower())
    tokens = [t for t in tokens if t]
    if not tokens:
        return True
    return all(t in FILLER_WORDS for t in tokens)


# ---------------------------------------------------------------------------
# Text substitutions  (order matters – more specific first)
# ---------------------------------------------------------------------------

TEXT_FIXES = [
    # Stutter fixes
    ("normaal gesproken no-no-normaal gesproken", "normaal gesproken"),
    ("k-can you briefly j-just describe", "can you briefly just describe"),
    ("wi-within", "within"),
    ("di-differ", "differ"),
    # ASR errors
    ("NCSE", "NKC"),           # ASR mishear of the organisation name
    ("Encase,", "NKC,"),       # "NKC" spoken → ASR renders as "Encase"
    ("back office systemsOurselves", "back office systems ourselves"),
    ("givenAnd", "given. And"),
    # Artefact from merging the lone-comma [Them] fragment
    (" , ", ", "),
]


def apply_fixes(text: str) -> str:
    for old, new in TEXT_FIXES:
        text = text.replace(old, new)
    return text


# ---------------------------------------------------------------------------
# Parse, process, serialise
# ---------------------------------------------------------------------------

SPEAKER_RE = re.compile(r"^\[(Me|Them)\]$")


def parse_turns(text: str) -> list[tuple[str, str]]:
    """Parse transcript into list of (speaker, content) tuples."""
    turns: list[tuple[str, str]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if SPEAKER_RE.match(line):
            speaker = line
            i += 1
            content_lines: list[str] = []
            while i < len(lines) and not SPEAKER_RE.match(lines[i].strip()):
                content_lines.append(lines[i])
                i += 1
            content = "\n".join(content_lines).strip()
            turns.append((speaker, content))
        else:
            i += 1
    return turns


def process(turns: list[tuple[str, str]]) -> list[tuple[str, str]]:
    result: list[list[str]] = []  # mutable pairs

    for speaker, content in turns:
        # Remove [Me]-only filler turns
        if speaker == "[Me]" and is_filler_only(content):
            continue

        # Merge with previous turn if same speaker
        if result and result[-1][0] == speaker:
            sep = " " if result[-1][1] and content else ""
            result[-1][1] = result[-1][1] + sep + content
        else:
            result.append([speaker, content])

    return [(s, c) for s, c in result]


def serialise(turns: list[tuple[str, str]]) -> str:
    parts: list[str] = []
    for speaker, content in turns:
        content = apply_fixes(content)
        parts.append(f"{speaker}\n{content}\n")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python clean_transcript.py <transcript.md> [--dry-run]")
        sys.exit(1)

    path = Path(sys.argv[1])
    dry_run = "--dry-run" in sys.argv

    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    original = path.read_text(encoding="utf-8")
    turns = parse_turns(original)
    processed = process(turns)
    output = serialise(processed)

    removed = len(turns) - len(processed)
    print(f"Turns before: {len(turns)}")
    print(f"Turns after:  {len(processed)}")
    print(f"Turns removed/merged: {removed}")

    original_lines = len(original.splitlines())
    output_lines = len(output.splitlines())
    print(f"Lines before: {original_lines}")
    print(f"Lines after:  {output_lines}")
    print(f"Lines reduced by: {original_lines - output_lines}")

    if dry_run:
        print("\n--- DRY RUN: no changes written ---")
    else:
        path.write_text(output, encoding="utf-8")
        print(f"\nSaved: {path}")


if __name__ == "__main__":
    main()
