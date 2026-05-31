"""Verify CGT realignment patches in Findings chapter."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
OUT = ROOT / ".cache" / "verify_findings_cgt.txt"


def main() -> None:
    md_path = ROOT / ".cache" / "thesis-current.md"
    subprocess.run(
        [
            "pandoc",
            str(DOCX),
            "-t",
            "markdown",
            "--track-changes=accept",
            "-o",
            str(md_path),
        ],
        check=True,
        capture_output=True,
    )
    text = md_path.read_text(encoding="utf-8")
    ch4 = text.split("# 4. Findings", 1)[-1].split("# 5.", 1)[0]

    banned = [
        "hard resources",
        "soft resources",
        "Affecting change",
        "Steering the organization",
        "Learning & experimentating",
        "Leveraging internal resources",
        "Navigating Obstacles",
        "absorb the organizational friction",
        "easier to think about automation if things are clear",
    ]
    required = [
        "Navigating internal conditions",
        "4.2.2",
        "Guiding the organization",
        "Mobilising internal conditions",
        "When conditions block progress",
        "Reading guide",
        "Supplier communication",
        "Coding development",
        "Mobilising infrastructure",
        "Enabling behavior",
    ]

    lines = ["=== Banned phrases (should be 0) ==="]
    for phrase in banned:
        count = len(re.findall(re.escape(phrase), ch4, re.IGNORECASE))
        lines.append(f"  {phrase!r}: {count}")
        if count:
            lines.append("    FAIL")

    lines.append("\n=== Required phrases ===")
    for phrase in required:
        found = phrase.lower() in ch4.lower()
        lines.append(f"  {phrase!r}: {'OK' if found else 'MISSING'}")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
