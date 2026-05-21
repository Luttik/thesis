"""Remove overlap fillers and merge split turns in [Me]/[Them] transcripts."""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Standalone turns to drop (overlap / backchannel only)
DROP_TURN_CONTENT = {
    "yeah",
    "yeah.",
    "yeah, yeah",
    "yeah, yeah.",
    "yes",
    "yes.",
    "mm",
    "mm.",
    "mm-hmm",
    "mm-hmm.",
    "mhm",
    "uh",
    "uh.",
    "okay",
    "okay.",
    "right",
    "right.",
    "sure",
    "cool",
    "nice",
    "oh",
    "oh.",
    "ah",
    "ah.",
    "ah, cool",
    "ah, cool.",
    "for sure.",
    "for sure",
    "definitely",
    "definitely.",
    "that's cool",
    "that's cool.",
    "all right",
    "all right.",
    "but-",
    "but-.",
    "[laughs]",
    "yeah. [laughs]",
}

SPEAKER_RE = re.compile(r"^\[(Me|Them)\]$|^> \*\[(Me|Them)\]\*$")
REDACTED = "[Redacted]"


def normalize_content(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def is_drop_turn(speaker: str, content: str) -> bool:
    if speaker not in ("[Me]", "[Them]"):
        return False
    c = content.strip()
    if not c:
        return True
    if c.startswith("> "):
        c = re.sub(r"^>\s*\*?|\*?$", "", c).strip()
    norm = normalize_content(c)
    if norm in DROP_TURN_CONTENT:
        return True
    # annotation-only
    if re.fullmatch(r"\[[\w\s]+\]", c):
        return True
    return False


def strip_me_markup(content: str) -> str:
    lines = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("> "):
            line = line[2:].strip()
        if line.startswith("*") and line.endswith("*"):
            line = line[1:-1].strip()
        lines.append(line)
    return "\n".join(lines).strip()


def format_me(content: str) -> str:
    text = strip_me_markup(content)
    if not text:
        return "> *[Me]*\n"
    return f"> *[Me]*\n> *{text}*"


def clean_inline_fillers(text: str) -> str:
    """Remove leading/trailing backchannels in substantive turns."""
    # Leading backchannel + comma
    text = re.sub(
        r"^(Yeah|Yes|Right|Okay|Cool|So),?\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    # Trailing backchannel
    text = re.sub(
        r",?\s+(yeah|yes|right|okay)\s*\.?\s*$",
        ".",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+yeah\.\s*$", ".", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+yeah,\s+yeah\.?\s*$", ".", text, flags=re.IGNORECASE)
    # Mid-sentence overlap: ?" Yeah. Who → ?" Who
    text = re.sub(r'(\?)"\s+Yeah\.\s+', r'\1" ', text)
    text = re.sub(r"(\?)\s+Yeah\.\s+", r"\1 ", text)
    # Duplicate stutters in Them text
    text = re.sub(r"\byeah-\s*\.\.\.", "...", text, flags=re.IGNORECASE)
    text = re.sub(r",\s+yeah,\s+", ", ", text, flags=re.IGNORECASE)
    text = re.sub(r"\byeah,\s+yeah\b", "yeah", text, flags=re.IGNORECASE)
    text = re.sub(r"Good that we planned a coffee\.\s+Yeah, so, yeah\.", "Good that we planned a coffee.", text)
    text = re.sub(r"Cool\.\s+Yeah\.\s+Maybe", "Maybe", text)
    text = re.sub(r"Yes\.\s+Yeah,\s+and", "And", text)
    text = re.sub(r"^Yeah\.\s+So", "So", text)
    text = re.sub(r"^Yeah\.\s+Who", "Who", text)
    text = re.sub(r"^Yeah\.\s+So-", "So", text)
    text = re.sub(r"Yeah,\s+yeah\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+yeah,\s+could be", " could be", text, flags=re.IGNORECASE)
    text = re.sub(r"but then yeah,\s+are you", "but are you", text, flags=re.IGNORECASE)
    text = re.sub(
        r"What would help\s+Yeah\.\s+And what would help",
        "What would help",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+\.\.\.\s+", " ... ", text)
    return text.strip()


def parse_blocks(text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line == REDACTED:
            blocks.append((REDACTED, ""))
            i += 1
            continue
        if line in ("[Me]", "[Them]") or line == "> *[Me]*":
            speaker = "[Me]" if "Me" in line else "[Them]"
            i += 1
            content_lines: list[str] = []
            while i < len(lines):
                nxt = lines[i].strip()
                if nxt in ("[Me]", "[Them]", REDACTED) or nxt == "> *[Me]*":
                    break
                content_lines.append(lines[i])
                i += 1
            blocks.append((speaker, "\n".join(content_lines).strip()))
        else:
            i += 1
    return blocks


def merge_consecutive_same(blocks: list[tuple[str, str]]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for speaker, content in blocks:
        if is_drop_turn(speaker, content):
            continue
        content = clean_inline_fillers(strip_me_markup(content) if speaker == "[Me]" else content)
        if not content and speaker != REDACTED:
            continue
        if out and out[-1][0] == speaker and speaker != REDACTED:
            prev = out[-1][1]
            sep = " " if prev and content else ""
            out[-1] = (speaker, prev + sep + content)
        else:
            out.append((speaker, content))
    return out


def render(blocks: list[tuple[str, str]]) -> str:
    parts: list[str] = []
    for speaker, content in blocks:
        if speaker == REDACTED:
            parts.append(f"{REDACTED}\n")
        elif speaker == "[Me]":
            parts.append(format_me(content))
        else:
            parts.append(f"[Them]\n{content}\n")
    return "\n\n".join(parts).rstrip() + "\n"


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "transcripts/Thesis interview Jeffrey Ploeg.md"
    )
    text = path.read_text(encoding="utf-8")
    blocks = parse_blocks(text)
    blocks = merge_consecutive_same(blocks)
    path.write_text(render(blocks), encoding="utf-8")
    print(f"Polished {path} ({len(blocks)} turns)")


if __name__ == "__main__":
    main()
