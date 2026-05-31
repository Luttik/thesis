"""List paragraphs near methodology §3.4."""

from __future__ import annotations

from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".cache" / "para-34.txt"


def main() -> None:
    d = Document(str(ROOT / "Thesis Draft - Daan Luttik - MBA.docx"))
    lines: list[str] = []
    for i, p in enumerate(d.paragraphs):
        t = p.text
        if any(
            k in t
            for k in (
                "3.4",
                "3.3",
                "Findings",
                "trustworthiness",
                "Trustworthiness",
                "Ensuring",
            )
        ):
            lines.append(f"{i}|{p.style.name}|{repr(t[:120])}")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(lines)} lines to {OUT}")


if __name__ == "__main__":
    main()
