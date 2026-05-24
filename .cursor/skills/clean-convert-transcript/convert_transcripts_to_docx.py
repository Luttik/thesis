"""Batch-convert Markdown transcript files to DOCX using pandoc.

Usage examples:
  # Convert all .md files in transcripts/
  python convert_transcripts_to_docx.py

  # Convert specific files
  python convert_transcripts_to_docx.py "transcripts/Thesis interview Erica.md"

  # Use a custom transcripts directory
  python convert_transcripts_to_docx.py --transcripts-dir path/to/transcripts
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

import typer

from quote_me_sections import quote_me_sections

app = typer.Typer(add_completion=False)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TRANSCRIPTS_DIR = PROJECT_ROOT / "transcripts"


def convert_md_to_docx(md_path: Path, *, update_markdown: bool = False) -> Path:
    docx_path = md_path.with_suffix(".docx")
    text = md_path.read_text(encoding="utf-8")
    formatted = quote_me_sections(text)

    if update_markdown and formatted != text:
        md_path.write_text(formatted, encoding="utf-8")

    subprocess.run(
        ["pandoc", "-f", "markdown", "-t", "docx", "-o", str(docx_path)],
        input=formatted,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return docx_path


def resolve_files(
    files: list[Path] | None,
    transcripts_dir: Path,
) -> list[Path]:
    if files:
        return [path.resolve() for path in files]

    if not transcripts_dir.is_dir():
        typer.echo(f"Transcripts directory not found: {transcripts_dir}", err=True)
        raise typer.Exit(1)

    md_files = sorted(transcripts_dir.glob("*.md"))
    if not md_files:
        typer.echo(f"No .md files found in {transcripts_dir}.", err=True)
        raise typer.Exit(0)

    return md_files


@app.command()
def main(
    files: list[Path] = typer.Argument(
        None,
        help="Markdown file(s) to convert; omit to convert all .md files in transcripts/",
    ),
    transcripts_dir: Path = typer.Option(
        DEFAULT_TRANSCRIPTS_DIR,
        "--transcripts-dir",
        help="Directory to scan when no files are specified",
    ),
    update_markdown: bool = typer.Option(
        False,
        "--update-markdown",
        help="Write [Me] italic block-quote formatting back to the .md source file",
    ),
) -> None:
    md_files = resolve_files(files, transcripts_dir)

    for md_path in md_files:
        if not md_path.exists():
            typer.echo(f"File not found: {md_path}", err=True)
            raise typer.Exit(1)
        if md_path.suffix.lower() != ".md":
            typer.echo(f"Skipping non-markdown file: {md_path}", err=True)
            raise typer.Exit(1)

        docx_path = md_path.with_suffix(".docx")
        typer.echo(f"Converting: {md_path.name} -> {docx_path.name}")
        try:
            convert_md_to_docx(md_path, update_markdown=update_markdown)
        except subprocess.CalledProcessError as exc:
            typer.echo(f"pandoc failed for {md_path.name} (exit code {exc.returncode})", err=True)
            raise typer.Exit(exc.returncode or 1) from exc

    typer.echo(f"Done. {len(md_files)} file(s) converted.")


if __name__ == "__main__":
    app()
