"""Remove interviewer filler-only lines from transcripts and merge adjacent Them: lines."""

import re
import sys
from pathlib import Path

FILLER_WORDS = {
    "yeah", "yep", "mhmm", "okay", "check", "sure", "cool", "interesting",
    "ja", "oké", "sí", "ya", "yes", "no", "nee", "ajá", "indeed", "exactly",
    "great", "zeker", "duidelijk", "for sure", "true", "nice", "right",
    "yep", "okey", "ok",
}

FILLER_PATTERN = re.compile(
    r"^Me:\s*"
    r"("
    + "|".join(re.escape(w) for w in sorted(FILLER_WORDS, key=len, reverse=True))
    + r")"
    r"[\s.,!?]*$",
    re.IGNORECASE,
)


def is_filler_only(line: str) -> bool:
    """Check if a Me: line contains only filler words (possibly repeated)."""
    stripped = line.strip()
    if not stripped.startswith("Me:"):
        return False
    content = stripped[3:].strip()
    if not content:
        return True
    tokens = re.split(r"[\s.,!?]+", content)
    tokens = [t for t in tokens if t]
    return all(t.lower() in FILLER_WORDS for t in tokens)


def clean_transcript(filepath: Path) -> dict:
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")

    new_lines: list[str] = []
    removed = 0
    merged = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if is_filler_only(stripped):
            removed += 1
            # Skip this line and any surrounding blank lines that would double up
            i += 1
            # Skip trailing blank lines after the removed filler
            while i < len(lines) and lines[i].strip() == "":
                i += 1
            # Check if we should merge: previous non-blank is Them: and next is Them:
            # Remove trailing blank from new_lines if it would create double blank
            while new_lines and new_lines[-1].strip() == "":
                new_lines.pop()

            # Check if we need to merge adjacent Them: lines
            if new_lines and new_lines[-1].strip().startswith("Them:"):
                next_line_idx = i
                if next_line_idx < len(lines) and lines[next_line_idx].strip().startswith("Them:"):
                    prev_content = new_lines[-1].strip()
                    next_content = lines[next_line_idx].strip()
                    # Merge: take content after "Them:" from second line
                    next_text = next_content[5:].strip()
                    merged_line = prev_content + " " + next_text
                    new_lines[-1] = merged_line + "  "
                    merged += 1
                    i = next_line_idx + 1
                    continue

            new_lines.append("")
            continue

        new_lines.append(line)
        i += 1

    # Clean up any triple+ blank lines
    cleaned: list[str] = []
    blank_count = 0
    for line in new_lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 2:
                cleaned.append(line)
        else:
            blank_count = 0
            cleaned.append(line)

    filepath.write_text("\n".join(cleaned), encoding="utf-8")
    return {
        "removed": removed,
        "merged": merged,
        "lines_before": len(lines),
        "lines_after": len(cleaned),
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python remove_fillers.py <file1.md> [file2.md] ...")
        sys.exit(1)

    for path_str in sys.argv[1:]:
        filepath = Path(path_str)
        if not filepath.exists():
            print(f"File not found: {filepath}")
            continue
        result = clean_transcript(filepath)
        print(f"{filepath.name}: removed={result['removed']}, merged={result['merged']}, "
              f"lines: {result['lines_before']} -> {result['lines_after']}")


if __name__ == "__main__":
    main()
