"""Replace named/numbered speaker labels with [Me] / [Them] in a transcript.

Usage examples:
  # See what speaker labels exist
  python normalize_speakers.py transcript.md --list-speakers

  # Remap and overwrite
  python normalize_speakers.py transcript.md --me "Speaker 1" --them "Speaker 0"

  # Multiple --them labels (e.g. group interview)
  python normalize_speakers.py transcript.md --me "Daan" --them "Erik" --them "Guest"

  # Preview without saving
  python normalize_speakers.py transcript.md --me "Speaker 1" --them "Speaker 0" --dry-run
"""

import re
import sys
from pathlib import Path

import typer

app = typer.Typer(add_completion=False)

SPEAKER_RE = re.compile(r"^\[([^\]]+)\]$")


def find_speakers(text: str) -> dict[str, int]:
    """Return speaker labels with occurrence counts, ordered by first appearance."""
    counts: dict[str, int] = {}
    for line in text.splitlines():
        m = SPEAKER_RE.match(line.strip())
        if m:
            label = m.group(1)
            counts[label] = counts.get(label, 0) + 1
    return counts


def normalize(text: str, me_labels: set[str], them_labels: set[str]) -> str:
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        m = SPEAKER_RE.match(stripped)
        if m:
            label = m.group(1)
            if label in me_labels:
                result.append("[Me]\n")
                continue
            if label in them_labels:
                result.append("[Them]\n")
                continue
        result.append(line)
    return "".join(result)


@app.command()
def main(
    file: Path = typer.Argument(..., help="Transcript markdown file to process"),
    me: str = typer.Option(None, "--me", help="Speaker label to map to [Me]"),
    them: list[str] = typer.Option(None, "--them", help="Speaker label(s) to map to [Them] (repeatable)"),
    list_speakers: bool = typer.Option(False, "--list-speakers", help="Print unique speaker labels and exit"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print result instead of overwriting"),
) -> None:
    if not file.exists():
        typer.echo(f"File not found: {file}", err=True)
        raise typer.Exit(1)

    text = file.read_text(encoding="utf-8")
    speakers = find_speakers(text)

    if list_speakers:
        if not speakers:
            typer.echo("No speaker labels found (pattern: [Label] on its own line).")
        else:
            typer.echo("Speaker labels found (count = times label appears on its own line):")
            for label, count in speakers.items():
                note = "  [likely action annotation]" if count <= 2 else ""
                typer.echo(f"  [{label}]  ({count}x){note}")
        raise typer.Exit(0)

    if not me and not them:
        typer.echo("Provide --me and/or --them, or use --list-speakers.", err=True)
        raise typer.Exit(1)

    me_set = {me} if me else set()
    them_set = set(them) if them else set()

    unknown = (me_set | them_set) - set(speakers.keys())
    if unknown:
        typer.echo(f"Warning: these labels were not found in the file: {unknown}", err=True)

    result = normalize(text, me_set, them_set)

    if dry_run:
        typer.echo(result)
    else:
        file.write_text(result, encoding="utf-8")
        replaced = sum(1 for s in (me_set | them_set) if s in speakers)
        skipped = set(speakers.keys()) - me_set - them_set - {"Me", "Them"}
        typer.echo(f"Updated {file}  ({replaced} label(s) remapped)")
        if skipped:
            typer.echo(f"Left unchanged: {sorted(skipped)}")


if __name__ == "__main__":
    app()
