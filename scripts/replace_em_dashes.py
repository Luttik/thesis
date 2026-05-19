"""Replace em-dashes in transcript text with commas or parentheses."""

from __future__ import annotations

import sys
from pathlib import Path

# Order matters: longer / more specific patterns first.
REPLACEMENTS: list[tuple[str, str]] = [
    (" — I mean — ", " (I mean) "),
    (" — as a human — ", " (as a human) "),
    (" — that acquisition engine — ", " (that acquisition engine) "),
    (" — those who produce for us. ", " (those who produce for us). "),
    (" — 'keep in control' isn't the right way to put it — ", " ('keep in control' isn't the right way to put it) "),
    (" — a data bottleneck — ", " (a data bottleneck) "),
    (" — I often call it a marketing ecosystem — ", " (I often call it a marketing ecosystem) "),
    ("platform strate— we are", "platform strategy. We are"),
    ("facili— facility", "facility"),
    (" — yes, the click-through — ", " (yes, the click-through) "),
    ("Print.com — taking Print.com as a label", "Print.com, taking Print.com as a label"),
    ("including Reclameland — yes", "including Reclameland, yes"),
    ("via e-commerce — well", "via e-commerce, well"),
    ("going to tran — that", "going to transform, that"),
    ("Traffic comes from — right", "Traffic comes from, right"),
    ("talking about — and I also", "talking about, and I also"),
    ("gets done — that naturally", "gets done, that naturally"),
    ("comparisons — where and how", "comparisons, where and how"),
    ("trustworthy party — yes", "trustworthy party, yes"),
    ("if I look at — so", "if I look at, so"),
    ("limitations, so — So", "limitations, so. So"),
    ("now is — look", "now is, look"),
    ("that order — you throw", "that order, you throw"),
    ("The webshop — and you also", "The webshop, and you also"),
    ("come to think — hey", "come to think, hey"),
    ("about AI — how do you", "about AI: how do you"),
    ("will this do — and I keep", "will this do, and I keep"),
    ("people will — maybe not yet", "people will, maybe not yet"),
    ("we — it's very specifically", "we, it's very specifically"),
    ("initially feels — but this", "initially feels, but this"),
    ("where do you — as a human — want", "where do you (as a human) want"),
    ("earlier — I'm reasonably good", "earlier, I'm reasonably good"),
    ("Supermetrics — because", "Supermetrics, because"),
    ("just to confirm — everything", "just to confirm, everything"),
    ("if it's not — it's indeed", "if it's not, it's indeed"),
    ("itself — well, there are", "itself, well, there are"),
    ("we now have — we have Slack", "we now have, we have Slack"),
    ("assortment — stickers", "assortment, stickers"),
    ("have color — and then", "have color, and then"),
    ("so much — because all those", "so much, because all those"),
    ("it's more — I think", "it's more, I think"),
    ("so what — it sounded", "so what, it sounded"),
    ("automation — based on", "automation, based on"),
    ("talking about — you're working", "talking about, you're working"),
    ("domain knowledge — and with", "domain knowledge, and with"),
    ("well yes — there are", "well yes, there are"),
    ("indeed — it just took", "indeed, it just took"),
    ("see a — and here", "see a, and here"),
    ("yes — that data engineer", "yes, that data engineer"),
    ("Partly — yes, now", "Partly, yes, now"),
    ("use it again — toward", "use it again, toward"),
    ("And now — no, okay", "And now, no, okay"),
    ("things. So —", "things. So"),
    ("let's say — but we're", "let's say, but we're"),
    ("is it —", "is it,"),
    ("speak — with other", "speak, with other"),
    ("not — look, we have", "not, look, we have"),
    ("within that, right — on the one", "within that, right, on the one"),
    ("documents — let's say", "documents, let's say"),
    ("is mainly — the foundation", "is mainly, the foundation"),
    ("other side, right — what do", "other side, right, what do"),
    ("appearance — we find", "appearance. We find"),
    ("less work — let me", "less work, let me"),
    ("things — you can", "things, you can"),
    ("everyone or so — well", "everyone or so, well"),
    ("those — I don't know", "those, I don't know"),
    ("me this — so", "me this, so"),
    ("I don't know — we're", "I don't know, we're"),
    ("see the —", "see the,"),
    ("The other side I think — there", "The other side I think, there"),
    ("governance is a bit lacking in the world sometimes, —", "governance is a bit lacking in the world sometimes,"),
    ("data infrastructure — as an enabler?", "data infrastructure, as an enabler?"),
    ("What is your —", "What is your..."),
    (" — ", ", "),
    ("—", ", "),
]


def replace_in_text(text: str) -> str:
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    return text


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).resolve().parents[1]
        / "transcripts"
        / "Thesis interview Sylvia Vroklage.md"
    )
    text = path.read_text(encoding="utf-8")
    before = text.count("—")
    fixed = replace_in_text(text)
  # cleanup double commas
    while ", ," in fixed:
        fixed = fixed.replace(", ,", ",")
    while "  " in fixed:
        fixed = fixed.replace("  ", " ")
    path.write_text(fixed, encoding="utf-8")
    print(f"{path.name}: em-dashes {before} -> {fixed.count('—')}")


if __name__ == "__main__":
    main()
