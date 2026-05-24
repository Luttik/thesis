"""Turn all [Me] sections in a transcript into italic markdown block quotes."""

import argparse
from pathlib import Path


def italicize(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return text
    if stripped.startswith("*") and stripped.endswith("*") and len(stripped) >= 2:
        return text
    return f"*{text}*"


def quote_me_sections(text: str) -> str:
    lines = text.splitlines(keepends=True)
    in_me_section = False
    result: list[str] = []

    for line in lines:
        stripped = line.strip()

        if stripped in {"[Me]", "> [Me]", "> *[Me]*"}:
            in_me_section = True
            result.append("> " + italicize("[Me]") + "\n")
            continue

        if stripped in {"[Them]", "> [Them]", "> *[Them]*"}:
            in_me_section = False
            result.append("[Them]\n")
            continue

        if in_me_section and stripped:
            content = stripped[2:] if stripped.startswith("> ") else line.rstrip("\n")
            result.append("> " + italicize(content) + "\n")
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
