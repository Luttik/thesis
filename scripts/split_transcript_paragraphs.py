"""Split overly long [Me]/[Them] transcript blocks into shorter paragraphs."""

from __future__ import annotations

import re
import sys
from pathlib import Path

MAX_CHARS = 480
MIN_CHARS_BEFORE_SPLIT = 220

ME_HEADER = re.compile(r"^> \*\[Me\]\*$")
THEM_HEADER = re.compile(r"^\[Them\]$")
ME_LINE = re.compile(r"^> \*(.+)\*$")


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def chunk_sentences(sentences: list[str]) -> list[str]:
    paragraphs: list[str] = []
    current: list[str] = []
    length = 0

    for sentence in sentences:
        sentence_len = len(sentence)
        if (
            current
            and length + sentence_len > MAX_CHARS
            and length >= MIN_CHARS_BEFORE_SPLIT
        ):
            paragraphs.append(" ".join(current))
            current = [sentence]
            length = sentence_len
        else:
            current.append(sentence)
            length += sentence_len + (1 if current else 0)

    if current:
        paragraphs.append(" ".join(current))
    return paragraphs


def split_text(text: str) -> list[str]:
    stripped = text.strip()
    if len(stripped) <= MAX_CHARS:
        return [stripped]
    return chunk_sentences(split_sentences(stripped))


def parse_blocks(lines: list[str]) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if ME_HEADER.match(line):
            i += 1
            content_lines: list[str] = []
            while i < len(lines):
                m = ME_LINE.match(lines[i].strip())
                if m:
                    content_lines.append(m.group(1))
                    i += 1
                elif not lines[i].strip():
                    i += 1
                else:
                    break
            blocks.append(("[Me]", "\n".join(content_lines)))
        elif THEM_HEADER.match(line):
            i += 1
            content_lines: list[str] = []
            while i < len(lines):
                nxt = lines[i].strip()
                if ME_HEADER.match(nxt) or THEM_HEADER.match(nxt):
                    break
                if nxt:
                    content_lines.append(lines[i].rstrip())
                i += 1
            blocks.append(("[Them]", "\n".join(content_lines)))
        else:
            i += 1
    return blocks


def render_me(paragraphs: list[str]) -> list[str]:
    out = ["> *[Me]*"]
    for i, para in enumerate(paragraphs):
        if i > 0:
            out.append("")
        out.append(f"> *{para}*")
    return out


def render_them(paragraphs: list[str]) -> list[str]:
    out = ["[Them]"]
    for i, para in enumerate(paragraphs):
        if i > 0:
            out.append("")
        out.append(para)
    return out


def process_file(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    blocks = parse_blocks(lines)
    output: list[str] = []
    splits = 0

    for speaker, content in blocks:
        paragraphs = split_text(content.replace("\n\n", " ").replace("\n", " "))
        if len(paragraphs) > 1:
            splits += 1
        rendered = render_me(paragraphs) if speaker == "[Me]" else render_them(paragraphs)
        if output:
            output.append("")
        output.extend(rendered)

    path.write_text("\n".join(output) + "\n", encoding="utf-8")
    print(f"Split {splits} long turns in {path}")


def main() -> None:
    target = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path("transcripts/Thesis interview Karin Boon.md")
    )
    process_file(target)


if __name__ == "__main__":
    main()
