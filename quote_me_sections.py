"""Turn all [Me] sections in a transcript into markdown block quotes."""

import argparse
import re
from pathlib import Path


def quote_me_sections(text: str) -> str:
    lines = text.splitlines(keepends=True)
    in_me_section = False
    result: list[str] = []

    for line in lines:
        stripped = line.strip()

        if stripped == "[Me]":
            in_me_section = True
            result.append("> " + line)
            continue

        if stripped == "[Them]":
            in_me_section = False
            result.append(line)
            continue

        if in_me_section and stripped:
            result.append("> " + line)
        else:
            result.append(line)

    return "".join(result)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert [Me] sections in transcripts to markdown block quotes."
    )
    parser.add_argument("files", nargs="+", type=Path, help="Markdown files to process")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the result instead of overwriting the file",
    )
    args = parser.parse_args()

    for path in args.files:
        text = path.read_text(encoding="utf-8")
        result = quote_me_sections(text)

        if args.dry_run:
            print(result)
        else:
            path.write_text(result, encoding="utf-8")
            print(f"Updated {path}")


if __name__ == "__main__":
    main()
