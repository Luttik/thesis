"""Correction-only ASR repetition and restart cleaning for transcripts."""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Words often repeated intentionally for emphasis — leave unchanged.
EMPHATIC_WORDS = frozenset(
    {
        "very",
        "so",
        "yeah",
        "no",
        "oh",
        "ah",
        "well",
        "now",
        "like",
        "right",
        "yes",
        "okay",
        "ok",
        "really",
        "just",
        "more",
    }
)

# Short function words that are almost always ASR stutter when repeated.
STUTTER_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "to",
        "in",
        "of",
        "for",
        "with",
        "on",
        "at",
        "is",
        "it",
        "that",
        "this",
        "i",
        "you",
        "we",
        "they",
        "he",
        "she",
        "my",
        "your",
        "our",
        "their",
        "what",
        "how",
        "when",
        "where",
        "who",
        "can",
        "could",
        "would",
        "should",
        "will",
        "do",
        "does",
        "did",
        "have",
        "has",
        "had",
        "be",
        "been",
        "being",
        "are",
        "was",
        "were",
        "if",
        "as",
        "by",
        "from",
        "not",
        "um",
        "uh",
        "e",
        "w",
    }
)

# Literal fixes for patterns that need context beyond regex (order matters).
POST_FIXES: list[tuple[str, str]] = [
    ("they where they were", "they were"),
    ("there's- is", "there is"),
    ("there'is", "there is"),
    ("could be do uh, could be", "could be"),
    ("my with the my", "my"),
    ("Yeah. So I, That is", "Yeah. So that is"),
    ("Yeah. So That is", "Yeah. So that is"),
    ("Yeah. So I-- That is good to ask", "Yeah. So that is good to ask"),
    ("what is that-- How", "what is that? How"),
    ("just loyal-- things", "just things"),
    ("acquisition team acquisition and strategy team", "acquisition and strategy team"),
    ("pro-- can", "can"),
    ("open question. what do", "open question. What do"),
    ("can you. Because", "can you? Because"),
    # Phase 2: ASR word merges and agentic misspellings
    ("for in-instance", "for instance"),
    ("in for-instance", "in for instance"),
    ("for in instance", "for instance"),
    ("pro most value", "the most value"),
    ("we'And we're", "we're"),
    ("we'And we", "we"),
    ("gentic AI", "agentic AI"),
    ("GenTech AI", "agentic AI"),
    ("a GenTech for", "agentic for"),
    ("use a GenTech for", "use agentic for"),
    ("use GenTech for", "use agentic for"),
    ("agendic AI", "agentic AI"),
    ("hygenic AI", "agentic AI"),
    ("agency AI", "agentic AI"),
]


def _should_collapse_word(word: str, *, stutter_only: bool = False) -> bool:
    lower = word.lower()
    if lower in EMPHATIC_WORDS:
        return False
    if stutter_only:
        return lower in STUTTER_WORDS
    return True


def fix_hyphen_restart(text: str) -> str:
    """Fix partial-word cutoffs: ``w- with`` -> ``with``, ``deep- dive`` -> ``deep dive``."""

    def repl(match: re.Match[str]) -> str:
        prefix, word = match.group(1), match.group(2)
        prefix_lower, word_lower = prefix.lower(), word.lower()
        if len(prefix) == 1:
            return word
        if word_lower.startswith(prefix_lower) and len(prefix) < len(word):
            return word
        # Trailing hyphen after a complete word: replace with a space, keep both parts.
        return f"{prefix} {word}"

    return re.sub(r"\b(\w+)-\s+(\w+)", repl, text)


def fix_double_dash_restart(text: str) -> str:
    """Fix short false starts with double dash: ``pro-- can`` -> ``can``."""

    def repl(match: re.Match[str]) -> str:
        prefix, word = match.group(1), match.group(2)
        # "I-- That" is a discourse restart, not a partial word.
        if prefix.lower() == "i":
            return match.group(0)
        if len(prefix) <= 2:
            return word
        return f"{prefix} {word}"

    return re.sub(r"\b(\w{1,2})--\s*(\w+)", repl, text)


def fix_word_double_dash_pause(text: str) -> str:
    """Turn mid-sentence ``word-- Next`` restarts into a clean sentence break."""
    return re.sub(
        r"\b(\w{2,})--\s+([A-Z])",
        r"\1. \2",
        text,
    )


def apply_post_fixes(text: str) -> str:
    """Literal fixes using word boundaries so ``gentic`` does not match inside ``agentic``."""
    for old, new in POST_FIXES:
        pattern = r"\b" + re.escape(old) + r"\b"
        text = re.sub(pattern, new, text, flags=re.IGNORECASE)
    return text


def _phrase_repeat_replacer(match: re.Match[str]) -> str:
    phrase = match.group(1)
    words = phrase.split()
    if len(words) == 1 and words[0].lower() in EMPHATIC_WORDS:
        return match.group(0)
    if len(words) == 1 and not _should_collapse_word(words[0]):
        return match.group(0)
    return phrase


def fix_phrase_repeat(text: str, *, max_words: int = 5) -> str:
    """Collapse repeated phrases: ``most of my, most of my`` -> ``most of my``."""
    pattern = rf"(\b[\w']+(?:\s+[\w']+){{0,{max_words - 1}}}),\s+\1\b"
    prev = None
    while prev != text:
        prev = text
        text = re.sub(pattern, _phrase_repeat_replacer, text, flags=re.IGNORECASE)
    return text


def fix_phrase_repeat_space(text: str, *, max_words: int = 5) -> str:
    """Collapse ``in the in the`` / ``what I what I`` style phrase stutters."""
    pattern = rf"(\b[\w']+(?:\s+[\w']+){{0,{max_words - 1}}})\s+\1\b"
    prev = None
    while prev != text:
        prev = text
        text = re.sub(pattern, _phrase_repeat_replacer, text, flags=re.IGNORECASE)
    return text


def fix_phrase_double_dash_overlap(text: str) -> str:
    """Collapse ``it's not the-- it's not a`` when speech restarts with shared prefix."""

    def repl(match: re.Match[str]) -> str:
        before, after = match.group(1), match.group(2)
        before_lower, after_lower = before.lower(), after.lower()
        if after_lower.startswith(before_lower):
            return after
        before_words = before.split()
        after_words = after.split()
        # Restart from the start of the phrase: ``it's not the-- it's not a``
        for n in range(min(len(before_words), len(after_words)), 0, -1):
            if [w.lower() for w in before_words[:n]] == [w.lower() for w in after_words[:n]]:
                return after
        for n in range(min(len(before_words), len(after_words)), 0, -1):
            suffix = " ".join(before_words[-n:]).lower()
            prefix = " ".join(after_words[:n]).lower()
            if suffix == prefix:
                return after
        return match.group(0)

    return re.sub(
        r"(\b[\w']+(?:\s+[\w']+){0,4})--\s+([\w']+(?:\s+[\w']+)*)",
        repl,
        text,
        flags=re.IGNORECASE,
    )


def fix_word_double_dash_repeat(text: str) -> str:
    """Collapse ``you-- you guide`` -> ``you guide``."""

    def repl(match: re.Match[str]) -> str:
        word = match.group(1)
        if word.lower() in EMPHATIC_WORDS:
            return match.group(0)
        return match.group(2)

    return re.sub(
        r"\b(\w+)--\s+(\1(?:\s+[\w']+)*)",
        repl,
        text,
        flags=re.IGNORECASE,
    )


def fix_word_repeat_comma(text: str, *, stutter_only: bool = False) -> str:
    """Collapse ``I, I`` / ``the, the`` style stutters."""

    def repl(match: re.Match[str]) -> str:
        word = match.group(1)
        if _should_collapse_word(word, stutter_only=stutter_only):
            return word
        return match.group(0)

    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"\b(\w+),\s+\1\b", repl, text, flags=re.IGNORECASE)
    return text


def fix_word_repeat_space(text: str, *, stutter_only: bool = False) -> str:
    """Collapse ``the the`` / ``I I`` style stutters."""

    def repl(match: re.Match[str]) -> str:
        word = match.group(1)
        if _should_collapse_word(word, stutter_only=stutter_only):
            return word
        return match.group(0)

    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"\b(\w+)\s+\1\b", repl, text, flags=re.IGNORECASE)
    return text


def clean_asr_repetitions(text: str) -> str:
    """Apply all correction-only ASR repetition fixes in a safe order."""
    text = fix_hyphen_restart(text)
    text = fix_double_dash_restart(text)
    text = fix_word_double_dash_repeat(text)
    text = fix_phrase_double_dash_overlap(text)
    text = fix_phrase_repeat(text)
    text = fix_phrase_repeat_space(text)
    text = fix_word_repeat_comma(text)
    # Space repeats are noisier; only collapse common function-word stutters.
    text = fix_word_repeat_space(text, stutter_only=True)
    text = fix_word_double_dash_pause(text)
    text = apply_post_fixes(text)
    return text


def clean_transcript_file(path: Path, *, dry_run: bool = False) -> tuple[str, str, int]:
    """Clean a full transcript file, preserving structure."""
    original = path.read_text(encoding="utf-8")
    cleaned = clean_asr_repetitions(original)
    changes = sum(1 for a, b in zip(original, cleaned, strict=False) if a != b)
    if not dry_run and cleaned != original:
        path.write_text(cleaned, encoding="utf-8")
    return original, cleaned, changes


def clean_directory(directory: Path, *, dry_run: bool = False) -> list[Path]:
    """Clean all ``.md`` files in *directory* (non-recursive). Returns changed paths."""
    if not directory.is_dir():
        raise NotADirectoryError(directory)
    changed: list[Path] = []
    for path in sorted(directory.glob("*.md")):
        original, cleaned, _ = clean_transcript_file(path, dry_run=True)
        if original == cleaned:
            print(f"  (no changes) {path.name}")
            continue
        if not dry_run:
            path.write_text(cleaned, encoding="utf-8")
        print(f"  {'[dry-run] ' if dry_run else ''}updated {path.name}")
        changed.append(path)
    return changed


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: python asr_repetition_cleaner.py <transcript.md | directory> [--dry-run]",
            file=sys.stderr,
        )
        sys.exit(1)

    path = Path(sys.argv[1])
    dry_run = "--dry-run" in sys.argv
    if not path.exists():
        print(f"Path not found: {path}", file=sys.stderr)
        sys.exit(1)

    if path.is_dir():
        print(f"Cleaning markdown in: {path}")
        changed = clean_directory(path, dry_run=dry_run)
        print(f"\n{'Would update' if dry_run else 'Updated'} {len(changed)} file(s).")
        return

    original, cleaned, _ = clean_transcript_file(path, dry_run=True)
    orig_count = len(re.findall(r"\b(\w+),\s+\1\b", original, re.I))
    new_count = len(re.findall(r"\b(\w+),\s+\1\b", cleaned, re.I))
    hyphen_orig = len(re.findall(r"\b\w+-\s+\w", original))
    hyphen_new = len(re.findall(r"\b\w+-\s+\w", cleaned))

    print(f"File: {path}")
    print(f"Characters before/after: {len(original):,} / {len(cleaned):,}")
    print(f"Word-comma repeats: {orig_count} -> {new_count}")
    print(f"Hyphen restarts: {hyphen_orig} -> {hyphen_new}")

    if original == cleaned:
        print("No changes needed.")
        return

    if dry_run:
        print("\n--- DRY RUN: no changes written ---")
        # Show a few diffs
        import difflib

        for line in difflib.unified_diff(
            original.splitlines(),
            cleaned.splitlines(),
            lineterm="",
            n=0,
        ):
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
                print(line)
                if sum(1 for _ in []) > 30:
                    break
    else:
        path.write_text(cleaned, encoding="utf-8")
        print(f"\nSaved: {path}")


if __name__ == "__main__":
    main()
