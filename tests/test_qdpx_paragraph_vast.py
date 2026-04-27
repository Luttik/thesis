import numpy as np

from thesis_cli.qdpx_paragraph_vast import (
    ParagraphRecord,
    SourceDoc,
    _has_overlap,
    rank_paragraphs,
    split_source_paragraphs,
)


def _record(
    paragraph_id: int,
    text: str,
    *,
    source_name: str = "Interview A",
    paragraph_index: int = 0,
    speaker: str = "Them",
    codes: list[str] | None = None,
) -> ParagraphRecord:
    return ParagraphRecord(
        paragraph_id=paragraph_id,
        source_guid="SRC",
        source_name=source_name,
        paragraph_index=paragraph_index,
        start=0,
        end=len(text),
        speaker=speaker,
        text=text,
        quote_hits=0,
        codes=codes or [],
    )


def test_split_source_paragraphs_keeps_offsets_and_speaker() -> None:
    src = SourceDoc(
        guid="S1",
        name="Doc",
        text="[Me] First line\n\n[Them] Second line\nPlain third\n",
    )

    spans = split_source_paragraphs(src)

    assert len(spans) == 3
    assert spans[0][0] == 0
    assert spans[0][3] == "Me"
    assert spans[0][4] == "[Me] First line"
    assert spans[1][3] == "Them"
    assert spans[1][4] == "[Them] Second line"
    assert spans[2][3] == "Unknown"
    assert src.text[spans[2][1] : spans[2][2]] == "Plain third"


def test_has_overlap_uses_open_interval_boundary() -> None:
    assert _has_overlap(10, 20, 15, 25)
    assert not _has_overlap(10, 20, 20, 30)


def test_rank_paragraphs_respects_filters_and_order() -> None:
    records = [
        _record(0, "agentic planning improves output", source_name="Doc A", paragraph_index=1),
        _record(1, "unrelated paragraph", source_name="Doc B", paragraph_index=2, speaker="Me"),
        _record(
            2,
            "workflow execution and planning",
            source_name="Doc A",
            paragraph_index=3,
            codes=["Agentic has: planning"],
        ),
    ]
    emb = np.array(
        [
            [1.0, 0.0],
            [0.0, 1.0],
            [0.9, 0.1],
        ],
        dtype=np.float32,
    )
    q = np.array([1.0, 0.0], dtype=np.float32)

    hits = rank_paragraphs(
        query="planning",
        q_vector=q,
        records=records,
        embeddings=emb,
        top_n=10,
        doc_filter="doc a",
        speaker_filter="any",
        code_filter="",
    )

    assert [h.record.paragraph_id for h in hits] == [0, 2]

    code_filtered = rank_paragraphs(
        query="planning",
        q_vector=q,
        records=records,
        embeddings=emb,
        top_n=10,
        doc_filter="",
        speaker_filter="any",
        code_filter="agentic has",
    )
    assert [h.record.paragraph_id for h in code_filtered] == [2]
