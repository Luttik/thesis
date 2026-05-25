"""Normalize transcript Markdown files.

Two passes are applied to every file in ``transcripts/``:

1. **Speaker turns** — Some transcripts use the legacy single-line format::

       Them: <content>
       Me:   <content>

   The thesis-wide standard for an interview turn is the block / quoted-italic
   form::

       [Them]
       <content>

       > *[Me]*
       > *<content>*

2. **Headings** — Any standalone heading line is dropped. This covers both
   plain markdown headings (e.g. ``## **Fluff**``, ``### Analytics Questions``)
   and "inline" headings nested in a quoted-italic block produced by the
   transcription tooling (e.g. ``> *## Job intro*``). After removal,
   consecutive blank lines are collapsed to a single blank line.

Files that already match the canonical format are left untouched. Run with::

    poetry run python scripts/normalize_transcripts.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS_DIR = ROOT / "transcripts"

# Match ``Me:`` / ``Them:`` only when they sit at the start of a line.
_ME_INLINE_RE = re.compile(r"^Me:\s*(.*?)\s*$")
_THEM_INLINE_RE = re.compile(r"^Them:\s*(.*?)\s*$")

# Plain Markdown ATX heading at the start of a line (e.g. ``## **Fluff**``).
_HEADING_RE = re.compile(r"^#{1,6}\s")

# Heading nested inside a transcript's quoted-italic block, written by the
# transcription tool (e.g. ``> *## Job intro*`` or ``> *# Part 2*``).
_QUOTED_HEADING_RE = re.compile(r"^>\s*\*?\s*#{1,6}\s.*\*?\s*$")


@dataclass
class FileResult:
    path: Path
    me_inline: int
    them_inline: int
    headings_removed: int
    changed: bool


def _normalize_speaker_turns(lines: list[str]) -> tuple[list[str], int, int]:
    """Rewrite legacy ``Me:`` / ``Them:`` lines to the standard format."""
    out: list[str] = []
    me_count = 0
    them_count = 0
    for line in lines:
        m_me = _ME_INLINE_RE.match(line)
        if m_me is not None:
            content = m_me.group(1)
            out.append("> *[Me]*")
            out.append(f"> *{content}*" if content else "> *")
            me_count += 1
            continue
        m_them = _THEM_INLINE_RE.match(line)
        if m_them is not None:
            content = m_them.group(1)
            out.append("[Them]")
            out.append(content)
            them_count += 1
            continue
        out.append(line)
    return out, me_count, them_count


def _strip_headings(lines: list[str]) -> tuple[list[str], int]:
    """Drop heading lines and collapse the resulting consecutive blank lines."""
    kept: list[str] = []
    removed = 0
    for line in lines:
        if _HEADING_RE.match(line) or _QUOTED_HEADING_RE.match(line):
            removed += 1
            continue
        kept.append(line)

    collapsed: list[str] = []
    prev_blank = False
    for line in kept:
        is_blank = line.strip() == ""
        if is_blank and prev_blank:
            continue
        collapsed.append(line)
        prev_blank = is_blank
    return collapsed, removed


def _normalize_file(path: Path) -> FileResult:
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines()
    lines, me_count, them_count = _normalize_speaker_turns(lines)
    lines, headings_removed = _strip_headings(lines)
    new_text = "\n".join(lines) + "\n"
    changed = new_text != original
    if changed:
        path.write_text(new_text, encoding="utf-8")
    return FileResult(
        path=path,
        me_inline=me_count,
        them_inline=them_count,
        headings_removed=headings_removed,
        changed=changed,
    )


def main() -> None:
    results: list[FileResult] = []
    for path in sorted(TRANSCRIPTS_DIR.glob("*.md")):
        results.append(_normalize_file(path))

    touched = [r for r in results if r.changed]
    untouched = [r for r in results if not r.changed]

    print("Normalized:")
    if not touched:
        print("  (no files needed changes)")
    for r in touched:
        print(
            f"  {r.path.name:55s} "
            f"Me: {r.me_inline:>3d}  Them: {r.them_inline:>3d}"
        )

    print(f"\nAlready in standard format: {len(untouched)} file(s).")


if __name__ == "__main__":
    main()
