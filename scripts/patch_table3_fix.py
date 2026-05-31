"""Patch remaining table 3 cell fixes."""

from __future__ import annotations

from docx import Document

from patch_findings_cgt import DOCX_PATH, TABLE3_UPDATES, patch_table3


def main() -> None:
    extra = {
        (11, 1): "Building specification capability",
        (11, 2): "Mobilising internal conditions",
        (4, 2): "Enabling behavior",
    }
    TABLE3_UPDATES.update(extra)
    doc = Document(str(DOCX_PATH))
    patch_table3(doc)
    doc.save(str(DOCX_PATH))
    print("Table 3 cells updated")


if __name__ == "__main__":
    main()
