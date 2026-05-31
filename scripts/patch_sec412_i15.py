"""Patch §4.1.2 I15 consumer-agent quotes (purchase + MCP reorder)."""

from __future__ import annotations

from docx import Document
from docx.text.paragraph import Paragraph

from patch_findings_cgt import (
    DOCX_PATH,
    find_para,
    insert_blocks,
    remove_following_until,
    replace_section,
)


def remove_paragraph(paragraph: Paragraph) -> None:
    paragraph._element.getparent().remove(paragraph._element)


I15_BLOCKS = [
    (
        "body",
        "Looking further ahead, some interviewees described a shift that is not yet "
        "operational at scale but is already shaping how they think and invest. "
        "Interviewee 15, a CMO at an e-commerce print company, articulated both the "
        "destination and an early prototype. She expects consumer-facing agents not "
        "only to research and compare but eventually to complete purchases on the "
        "customer's behalf:",
    ),
    (
        "quote",
        "there's no longer doing business with a human. But there's a bot, a project, "
        "an artifact, whatever we're going to call it. Yes, that goes to the platform. "
        "The platform therefore probably also needs to look different. And it's going "
        "to search for information, select a product, make comparisons. So that for me "
        "is the further form of agentic AI.",
    ),
    ("attr", "— Interviewee 15"),
    (
        "body",
        "Comparison and selection, in her account, are steps toward a transactional "
        "end state—not the end state itself. She continued:",
    ),
    (
        "quote",
        "I think people are going to use this much more to come to decisions and make "
        "purchases to some extent. So people will, maybe not yet, but later they'll just "
        "give their credit card details to an LLM and it's going to buy things for them "
        "on request. Or maybe even on a schedule.",
    ),
    ("attr", "— Interviewee 15"),
    (
        "body",
        "To prepare for that channel, her team built an MCP connector that lets Claude "
        "pull prior orders from the webshop and place a personalized print reorder "
        "directly into the shopping cart:",
    ),
    (
        "quote",
        "you can couple connectors to Claude... tell Claude: okay, fetch all my orders "
        "from [company]. And I want to reorder that order. And then via that connector "
        "it actually reorders that order, you throw it into my shopping cart. Um, I add "
        "a print file myself and I ultimately want to pay myself... I see that as the "
        "future, so to speak. It's a new channel, we need to facilitate that.",
    ),
    ("attr", "— Interviewee 15"),
    (
        "body",
        "This scenario is mostly anticipated at industry scale: few organizations in the "
        "data have seen consumer-owned purchasing agents at volume. Its importance lies "
        "in how it is already motivating concrete investment—including the connector "
        "work discussed again in §4.1.3 from the supplier-standards angle.",
    ),
]

SUPPLIER_TAIL = [
    (
        "body",
        "Concrete supplier releases act as direct triggers for new initiatives. New "
        "technical standards — particularly MCP-compatible connectors and integrations "
        "— are routinely turning abstract AI capability into immediately deployable use "
        "cases. Interviewee 15's webshop connector (§4.1.2) was enabled in part by newly "
        "available MCP integration standards—a pattern several participants described "
        "where a supplier release, rather than an internally generated idea, becomes the "
        "proximate trigger for a new agentic initiative. In this pattern, suppliers do not "
        "merely provide tools — they also define which use cases become organizationally "
        "legible as 'agentic.'",
    ),
]


def replace_through(
    before: Paragraph, stop: Paragraph, blocks: list[tuple[str, str]]
) -> None:
    """Remove all paragraphs after before until stop, then insert blocks."""
    remove_following_until(before, stop)
    insert_blocks(before, blocks)


def find_para_before(doc: Document, needle: str) -> Paragraph:
    target = find_para(doc, needle)
    prev_el = target._element.getprevious()
    if prev_el is None:
        raise ValueError(f"No paragraph before: {needle[:60]}")
    for p in doc.paragraphs:
        if p._element is prev_el:
            return p
    raise ValueError("Previous paragraph not found")


def main() -> None:
    doc = Document(str(DOCX_PATH))

    stop = find_para(doc, "4.1.3", heading=True)
    anchor = find_para(doc, "paid search are")
    replace_through(anchor, stop, I15_BLOCKS)

    supplier_intro_end = find_para(doc, "abstract use case immediately actionable")
    closing = find_para(doc, "Together, these external conditions motivate")
    if "Interviewee 15's webshop connector" not in supplier_intro_end.text:
        replace_section(supplier_intro_end, closing, SUPPLIER_TAIL)

    out = DOCX_PATH
    try:
        doc.save(str(out))
    except PermissionError:
        out = DOCX_PATH.parent / ".cache" / "thesis_i15_patch.docx"
        doc.save(str(out))
        print(f"Main docx locked — saved to {out}")
        return
    print(f"Patched I15 quotes in {out}")


if __name__ == "__main__":
    main()
