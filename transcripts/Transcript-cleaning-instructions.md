# Transcript cleaning instructions

Use this as the single source of truth when cleaning thesis interview or debrief transcripts (in Cursor or manually). Apply the same rules to every chunk so cleaning is consistent.

## Format

- Speaker labels: `Me:` and `Them:` (or named speakers), one turn per line.
- Header at top: Meeting Title, Date, Meeting participants, then "Transcript:" and content.

## Do

| Action | Example |
|--------|--------|
| Fix clear ASR errors (wrong word that changes meaning) | "Este" → "Yes" where intended |
| Fix obvious stutter repetition in the **same** word | "I I " → "I ", "the the " → "the " |
| Normalize speaker labels if needed | Consistent `Me:` / `Them:` |
| One turn per line, consistent blank lines | Preserve structure |
| Optional: fix punctuation that breaks readability | Missing period at end of turn |
| Improve excessive fillers | Leave some fillers to show unclarity, but clean up when multiple fillers and restarts make a sentence almost unreadable |
| Fix "agentic" misspellings | ASR often transcribes "agentic" as "agency", "hygenic", "agendic", etc. Use context to determine if it should be "agentic" |
| **Remove interviewer filler-only lines** | Remove `Me:` lines containing only acknowledgment words (Yeah, Yep, Mhmm, Okay, Check, Sure, Cool, Interesting, Ja, Oké, Sí, Ya, Yes, No, Nee, Ajá, Indeed, Exactly, Great, Zeker, Duidelijk — and repeated combinations). Keep lines where filler is followed by substantive content (e.g. "Me: Yeah. So what I'm researching...") |
| **Merge adjacent `Them:` lines after filler removal** | When removing a filler line leaves two adjacent `Them:` lines, merge them into one turn (the split was artificial) |

## Do not

| Do not | Reason |
|--------|--------|
| Remove fillers *within* substantive lines | Part of the dataset; they indicate the speaker's flow and emphasis |
| Remove `Them:` filler lines | Interviewee speech patterns are data; only interviewer fillers are removed |
| Rewrite or "improve" participants' wording | Preserve what was said |
| Change meaning or add interpretation | Correction only |
| Merge or split substantive content | Keep turns as-is (only merge `Them:` lines that were split by a removed filler) |
| Normalize language (e.g. translate Dutch to English) | Unless you explicitly decide otherwise |

## Thesis write-ups

When you include quotes in the thesis and omit parts, use square brackets: `[...]`. That is for the write-up phase, not for the transcript cleaning step.

## Chunked cleaning

When cleaning a **chunk** of a transcript:

- Chunk 1: Keep the full header (Meeting Title, Date, participants, "Transcript:") and the first N turns.
- Chunk 2, 3, …: Continuation only (no duplicate header). Preserve exact line format and blank lines so merge is seamless.
