"""Remove duplicate Table 3 trustworthiness tables; keep one after the title paragraph."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table

ROOT = Path(__file__).resolve().parents[1]
DOCX_PATH = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"

TRUST_HDR = "Criteria of trustworthiness"
TITLE = "Trustworthiness assessment."


def is_trust_table(tbl_el) -> bool:
    texts = [t.text or "" for t in tbl_el.iter(qn("w:t"))]
    combined = "".join(texts)
    return TRUST_HDR in combined


def main() -> None:
    doc = Document(str(DOCX_PATH))
    body = doc.element.body

    title_el = None
    for child in body:
        if child.tag.endswith("}p"):
            text = "".join(t.text or "" for t in child.iter(qn("w:t"))).strip()
            if text == TITLE:
                title_el = child
                break

    if title_el is None:
        raise SystemExit(f"Could not find paragraph: {TITLE!r}")

    # Collect trust tables immediately following the title (before Findings heading).
    following_trust: list = []
    sibling = title_el.getnext()
    while sibling is not None:
        if sibling.tag.endswith("}p"):
            text = "".join(t.text or "" for t in sibling.iter(qn("w:t"))).strip()
            if text.startswith("4.") and "Findings" in text:
                break
        if sibling.tag.endswith("}tbl") and is_trust_table(sibling):
            following_trust.append(sibling)
        sibling = sibling.getnext()

    # Remove extras after title; keep the first.
    for extra in following_trust[1:]:
        extra.getparent().remove(extra)

    # Remove any other trust tables in the document (orphans from re-runs).
    kept_after_title = following_trust[0] if following_trust else None
    for child in list(body):
        if child.tag.endswith("}tbl") and is_trust_table(child):
            if child is not kept_after_title:
                child.getparent().remove(child)

    if kept_after_title is None:
        raise SystemExit("No trustworthiness table found; run convert_trustworthiness_table.py")

    remaining = sum(1 for t in doc.tables if TRUST_HDR in t.rows[0].cells[0].text)
    doc.save(str(DOCX_PATH))
    print(f"Kept 1 trustworthiness table; removed duplicates. Remaining trust tables: {remaining}")


if __name__ == "__main__":
    main()
