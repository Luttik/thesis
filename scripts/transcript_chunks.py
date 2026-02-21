#!/usr/bin/env python3
"""
Split transcripts by speaker turns, merge cleaned chunks, and optionally apply
deterministic pre-pass fixes. Use with Cursor transcript-cleaning workflow.
"""

import argparse
import re
import sys
from pathlib import Path

# Safe stutter collapses: same word repeated at word boundary (space after).
_STUTTER_WORDS = ["I", "the", "we", "that", "is", "it", "to", "and", "you", "I'm", "Like"]
STUTTER_PATTERNS = [
    (re.compile(rf"\b({re.escape(w)})(?:\s+\1)+\s+"), r"\1 ") for w in _STUTTER_WORDS
]

# Known ASR errors: exact phrase -> replacement. Extend as needed.
ASR_REPLACEMENTS: list[tuple[str, str]] = [
    ("Este ", "Yes "),
    ("It shoots. ", "It does. "),
    ("This is most great.", "This is mostly great."),
]


def find_header_end(lines: list[str]) -> int:
    """Return index of first line that is a speaker turn (Me: or Them:)."""
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("Me:") or s.startswith("Them:"):
            return i
    return len(lines)


def is_speaker_line(line: str) -> bool:
    """True if line is a speaker turn (Me: or Them: at start)."""
    s = line.lstrip()
    return s.startswith("Me:") or s.startswith("Them:")


def split_into_turns(lines: list[str], header_end: int) -> tuple[list[str], list[list[str]]]:
    """
    Return (header_lines, list of turn_lines).
    Each turn is one or more lines; we treat each Me:/Them: line as one turn (content on same line).
    """
    header = lines[:header_end]
    rest = lines[header_end:]
    turns: list[list[str]] = []
    current: list[str] = []
    for line in rest:
        if is_speaker_line(line):
            if current:
                turns.append(current)
            current = [line]
        else:
            if current:
                current.append(line)
            # else: leading non-speaker line after header, attach to next turn or drop
            # Our format has one turn per line, so we don't expect this; still allow it
    if current:
        turns.append(current)
    return header, turns


def cmd_fix(path: Path, in_place: bool) -> None:
    """Apply deterministic fixes only. Write to stdout unless --in-place."""
    text = path.read_text(encoding="utf-8")
    for pattern, repl in STUTTER_PATTERNS:
        text = pattern.sub(repl, text)
    for old, new in ASR_REPLACEMENTS:
        text = text.replace(old, new)
    if in_place:
        path.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def cmd_split(
    path: Path,
    turns_per_chunk: int,
    out_dir: Path | None,
) -> None:
    """Split transcript into chunk files by speaker turn count."""
    lines = path.read_text(encoding="utf-8").splitlines()
    # Preserve trailing newline behavior: no trailing newline in splitlines()
    header_end = find_header_end(lines)
    header, turns = split_into_turns(lines, header_end)
    if not turns:
        print("No speaker turns found.", file=sys.stderr)
        sys.exit(1)
    out_dir = out_dir or path.parent
    base = path.stem
    suffix = path.suffix
    written = 0
    start = 0
    part = 1
    while start < len(turns):
        end = min(start + turns_per_chunk, len(turns))
        chunk_turns = turns[start:end]
        chunk_lines: list[str] = []
        if part == 1:
            chunk_lines.extend(header)
            chunk_lines.append("")
        for turn_lines in chunk_turns:
            chunk_lines.extend(turn_lines)
        out_path = out_dir / f"{base}-part{part}{suffix}"
        out_path.write_text("\n".join(chunk_lines) + "\n", encoding="utf-8")
        print(out_path, file=sys.stderr)
        written += 1
        start = end
        part += 1
    print(f"Wrote {written} chunk(s) to {out_dir}", file=sys.stderr)


def cmd_merge(glob_or_path: Path, output: Path | None, base: str | None = None) -> None:
    """
    Merge *-partN.md files into one. glob_or_path can be a directory (then we
    glob *-part*.md, or {base}-part*.md if --base is set) or a path pattern. Parts are sorted by N.
    """
    if glob_or_path.is_dir():
        pattern = f"{base}-part*.md" if base else "*-part*.md"
        part_files = sorted(glob_or_path.glob(pattern), key=_part_key)
    else:
        # Treat as literal file path for single file; for pattern we'd need glob
        parent = glob_or_path.parent
        pattern = glob_or_path.name
        part_files = sorted(parent.glob(pattern), key=_part_key)
    if not part_files:
        print("No *-part*.md files found.", file=sys.stderr)
        sys.exit(1)
    merged: list[str] = []
    for i, p in enumerate(part_files):
        lines = p.read_text(encoding="utf-8").splitlines()
        if i == 0:
            merged.extend(lines)
        else:
            # Skip header in continuation chunks (until first Me: or Them:)
            j = 0
            for j, line in enumerate(lines):
                if is_speaker_line(line):
                    break
            merged.extend(lines[j:])
        if i < len(part_files) - 1:
            merged.append("")
    out = output or (part_files[0].parent / f"{_base_name(part_files[0])}-merged.md")
    out.write_text("\n".join(merged).rstrip() + "\n", encoding="utf-8")
    print(f"Merged {len(part_files)} chunk(s) -> {out}", file=sys.stderr)


def _part_key(path: Path) -> tuple[int, str]:
    m = re.search(r"-part(\d+)", path.stem)
    return (int(m.group(1)), path.name) if m else (0, path.name)


def _base_name(path: Path) -> str:
    return re.sub(r"-part\d+$", "", path.stem)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transcript chunking: split by turns, merge parts, optional deterministic fix."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    fix_p = sub.add_parser("fix", help="Apply deterministic fixes (stutters, known ASR errors)")
    fix_p.add_argument("file", type=Path, help="Transcript file")
    fix_p.add_argument("--in-place", "-i", action="store_true", help="Overwrite file")

    split_p = sub.add_parser("split", help="Split transcript into chunks by speaker turn count")
    split_p.add_argument("file", type=Path, help="Transcript file")
    split_p.add_argument(
        "--turns", "-n", type=int, default=90, help="Speaker turns per chunk (default 90)"
    )
    split_p.add_argument(
        "--out-dir", "-o", type=Path, default=None, help="Output directory (default: same as file)"
    )

    merge_p = sub.add_parser("merge", help="Merge *-part*.md chunk files into one")
    merge_p.add_argument(
        "path",
        type=Path,
        help="Directory containing part files, or path pattern",
    )
    merge_p.add_argument(
        "--output", "-o", type=Path, default=None, help="Output file (default: <base>-merged.md)"
    )
    merge_p.add_argument(
        "--base",
        "-b",
        type=str,
        default=None,
        help="Only merge files matching <base>-part*.md (e.g. 'Thesis transcript Georgio Mosis')",
    )

    args = parser.parse_args()
    if args.command == "fix":
        cmd_fix(args.file, args.in_place)
    elif args.command == "split":
        cmd_split(args.file, args.turns, args.out_dir)
    elif args.command == "merge":
        cmd_merge(args.path, args.output, args.base)
    return 0


if __name__ == "__main__":
    sys.exit(main())
