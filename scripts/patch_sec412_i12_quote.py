"""Fix §4.1.2 I12 paraphrase — replace with actual block quote."""

from __future__ import annotations

from docx import Document

from patch_findings_cgt import DOCX_PATH, find_para, insert_blocks, remove_following_until

I12_BLOCKS = [
    (
        "body",
        "A further dimension of market pressure comes from shifting consumer "
        "behaviour. Interviewee 12 distinguished a third category—agents of "
        "customers—from marketer-controlled agents for customers, and considered "
        "it the most disruptive force on the horizon:",
    ),
    (
        "quote",
        "this is what I would call agents of customers... the end users, like, "
        "they actually have agents going and acting on their behalf... you're "
        "starting to see the emergence of agentic commerce... it's going to be a "
        "huge disruption for marketing because it's almost like we've got a new "
        "intermediary... between us as a seller and... the human buyer ultimately "
        "on the other side",
    ),
    ("attr", "— Interviewee 12"),
    (
        "body",
        "Most organizations in the data have not yet encountered this shift at "
        "scale, but it is widely anticipated and is already prompting investment "
        "in new channel designs and agentic customer engagement models.",
    ),
]


def main() -> None:
    doc = Document(str(DOCX_PATH))
    stop = find_para(doc, "Consumers expectations might change")
    anchor = find_para(doc, "not be left behind")
    remove_following_until(anchor, stop)
    insert_blocks(anchor, I12_BLOCKS)
    out = DOCX_PATH
    try:
        doc.save(str(out))
    except PermissionError:
        out = DOCX_PATH.parent / ".cache" / "thesis_i12_patch.docx"
        doc.save(str(out))
        print(f"Main docx locked — saved to {out}")
        return
    print(f"Fixed I12 attribution in {out}")


if __name__ == "__main__":
    main()
