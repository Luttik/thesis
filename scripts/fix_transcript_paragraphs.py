"""Merge awkward mid-sentence paragraph breaks in interview transcripts."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ME_LINE = re.compile(r"^>\s*\*(.+?)\s*\*\s*$")
SPEAKER_ONLY = re.compile(r"^\[?(Me|Them)\]?\s*$", re.IGNORECASE)
THEM_LABEL = "[Them]"


def _me_inner(line: str) -> str | None:
    m = ME_LINE.match(line.strip())
    if not m:
        return None
    inner = m.group(1).strip()
    if not inner or SPEAKER_ONLY.match(inner):
        return None
    return inner


def _ends_sentence(text: str) -> bool:
    t = text.rstrip()
    if not t:
        return True
    for suffix in ("[laughs]", "[laugh]", "[ding]", "[hangs up]", "[inaudible]"):
        if t.endswith(suffix):
            return True
    return t[-1] in ".!?"


def _is_short_fragment(text: str, max_len: int = 55) -> bool:
    t = text.strip()
    if len(t) < 25:
        return True
    return len(t) <= max_len and not _ends_sentence(t)


def _should_merge_paragraphs(prev: str, nxt: str) -> bool:
    prev = prev.strip()
    nxt = nxt.strip()
    if not prev or not nxt:
        return False
    if _ends_sentence(prev):
        if _is_short_fragment(nxt) and not _ends_sentence(nxt):
            return True
        if nxt[0].islower():
            return True
        return False
    if prev.endswith((",", ";", ":", "—")):
        return True
    if nxt[0].islower():
        return True
    if _is_short_fragment(prev) or _is_short_fragment(nxt):
        return True
    return True


def _merge_paragraphs(paragraphs: list[str]) -> list[str]:
    if not paragraphs:
        return []
    out: list[str] = [paragraphs[0].strip()]
    for para in paragraphs[1:]:
        para = para.strip()
        if not para:
            continue
        if _should_merge_paragraphs(out[-1], para):
            joiner = "" if out[-1].endswith("-") else " "
            out[-1] = f"{out[-1].rstrip()}{joiner}{para}"
        else:
            out.append(para)
    return out


def _merge_me_lines(lines: list[str]) -> list[str]:
    """Merge consecutive > *[Me]* lines into one block per utterance."""
    out: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        if not buf:
            return
        merged = _merge_paragraphs([" ".join(s.strip() for s in buf)])
        for para in merged:
            out.append("> *[Me]*")
            out.append(f"> *{para} *")
        buf = []

    for line in lines:
        inner = _me_inner(line)
        if inner is not None:
            buf.append(inner)
        elif line.strip() in {"> *[Me]*", "> *[Them]*"}:
            continue
        else:
            flush()
            out.append(line)
    flush()
    return out


def process_markdown(text: str) -> str:
    lines = text.splitlines()
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == THEM_LABEL:
            result.append(line)
            i += 1
            raw_paras: list[str] = []
            while i < len(lines):
                s = lines[i].strip()
                if s.startswith("> *"):
                    break
                if s == THEM_LABEL:
                    i += 1
                    continue
                if s == "":
                    if raw_paras and raw_paras[-1] != "\0":
                        raw_paras.append("\0")
                    i += 1
                    continue
                raw_paras.append(lines[i].strip())
                i += 1
            paras: list[str] = []
            cur: list[str] = []
            for p in raw_paras:
                if p == "\0":
                    if cur:
                        paras.append(" ".join(cur))
                        cur = []
                else:
                    cur.append(p)
            if cur:
                paras.append(" ".join(cur))
            for p in _merge_paragraphs(paras):
                result.append(p)
                result.append("")
            continue
        if line.strip().startswith("> *"):
            me_lines: list[str] = []
            while i < len(lines):
                s = lines[i].strip()
                if s == "":
                    i += 1
                    continue
                if s == THEM_LABEL:
                    break
                if s.startswith("> *"):
                    me_lines.append(lines[i])
                    i += 1
                    continue
                break
            for ml in _merge_me_lines(me_lines):
                result.append(ml)
                result.append("")
            continue
        result.append(line.rstrip())
        i += 1

    cleaned: list[str] = []
    for j, line in enumerate(result):
        if line == "" and (not cleaned or cleaned[-1] == ""):
            continue
        cleaned.append(line)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return "\n".join(cleaned) + "\n"


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        ROOT / "transcripts" / "Thesis interview Sylvia Vroklage.md"
    )
    before = path.read_text(encoding="utf-8").count("\n")
    fixed = process_markdown(path.read_text(encoding="utf-8"))
    path.write_text(fixed, encoding="utf-8")
    print(f"{path.name}: {before} -> {fixed.count(chr(10))} lines")


if __name__ == "__main__":
    main()
