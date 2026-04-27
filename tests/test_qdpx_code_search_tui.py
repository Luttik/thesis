import numpy as np

from thesis_cli.qdpx_code_search_tui import CodeSearchApp, rank_code_matches
from thesis_cli.qdpx_dedupe_tui import CodeRecord, QuoteSnippet


def _code(
    guid: str,
    name: str,
    full_name: str,
    description: str = "",
    quotes: list[QuoteSnippet] | None = None,
) -> CodeRecord:
    return CodeRecord(
        guid=guid,
        name=name,
        full_name=full_name,
        description=description,
        parent_guid=None,
        quotes=quotes or [],
    )


def _build_app(codes: list[CodeRecord]) -> CodeSearchApp:
    label_embeddings = np.array(
        [
            [1.0, 0.0],
            [0.0, 1.0],
            [0.5, 0.5],
        ],
        dtype=np.float32,
    )
    quote_embeddings = np.array(
        [
            [0.0, 1.0],
            [1.0, 0.0],
            [0.5, 0.5],
        ],
        dtype=np.float32,
    )
    return CodeSearchApp(
        codes=codes,
        label_embeddings=label_embeddings,
        quote_embeddings=quote_embeddings,
        model_name="fake-model",
        query_batch_size=1,
        weight_name=0.7,
        weight_quote=0.3,
        initial_query="",
        top_n=10,
        device="cpu",
    )


def test_rank_code_matches_returns_embedding_order_without_lexical_boost() -> None:
    codes = [
        _code("A", "alpha", "Group: alpha"),
        _code("B", "beta", "Group: beta"),
        _code("C", "gamma", "Group: gamma"),
    ]
    q_vector = np.array([1.0, 0.0], dtype=np.float32)

    indices, scores = rank_code_matches(
        query="zzz-not-found",
        codes=codes,
        q_vector=q_vector,
        label_embeddings=np.array([[1.0, 0.0], [0.0, 1.0], [0.6, 0.4]], dtype=np.float32),
        quote_embeddings=np.array([[0.2, 0.8], [0.9, 0.1], [0.2, 0.8]], dtype=np.float32),
        weight_name=0.7,
        weight_quote=0.3,
        top_n=0,
    )

    assert indices == [0, 2, 1]
    assert scores[0] > scores[1] > scores[2]


def test_rank_code_matches_uses_exact_name_lexical_boost() -> None:
    codes = [
        _code("A", "alpha", "Group: alpha"),
        _code("B", "beta", "Group: beta"),
    ]
    q_vector = np.array([0.0, 1.0], dtype=np.float32)

    indices, scores = rank_code_matches(
        query="alpha",
        codes=codes,
        q_vector=q_vector,
        label_embeddings=np.array([[0.0, 1.0], [0.0, 1.0]], dtype=np.float32),
        quote_embeddings=np.array([[0.0, 1.0], [0.0, 1.0]], dtype=np.float32),
        weight_name=0.5,
        weight_quote=0.5,
        top_n=10,
    )

    assert indices == [0, 1]
    assert scores[0] - scores[1] >= 4.9


def test_rank_code_matches_honors_top_n_limit() -> None:
    codes = [
        _code("A", "alpha", "Group: alpha"),
        _code("B", "beta", "Group: beta"),
        _code("C", "gamma", "Group: gamma"),
    ]

    indices, _ = rank_code_matches(
        query="nothing",
        codes=codes,
        q_vector=np.array([1.0, 0.0], dtype=np.float32),
        label_embeddings=np.eye(3, 2, dtype=np.float32),
        quote_embeddings=np.zeros((3, 2), dtype=np.float32),
        weight_name=1.0,
        weight_quote=0.0,
        top_n=2,
    )

    assert len(indices) == 2


def test_rank_code_matches_boosts_description_and_quote_hits() -> None:
    codes = [
        _code("A", "alpha", "Group: alpha"),
        _code("B", "beta", "Group: beta", description="Capturing market insight in interviews."),
        _code(
            "C",
            "gamma",
            "Group: gamma",
            quotes=[QuoteSnippet(source_name="Interview 1", text="This was an insight from users.")],
        ),
    ]

    indices, _ = rank_code_matches(
        query="insight",
        codes=codes,
        q_vector=np.array([0.0, 1.0], dtype=np.float32),
        label_embeddings=np.zeros((3, 2), dtype=np.float32),
        quote_embeddings=np.zeros((3, 2), dtype=np.float32),
        weight_name=0.5,
        weight_quote=0.5,
        top_n=10,
    )

    assert indices == [1, 2, 0]


def test_apply_search_results_ignores_stale_generation(monkeypatch) -> None:
    codes = [
        _code("A", "alpha", "Group: alpha"),
        _code("B", "beta", "Group: beta"),
        _code("C", "gamma", "Group: gamma"),
    ]
    app = _build_app(codes)
    app._search_generation = 2
    app.result_indices = [0]
    app.result_scores = [0.9]

    class DummyStatus:
        def __init__(self) -> None:
            self.messages: list[str] = []

        def update(self, message: str) -> None:
            self.messages.append(message)

    status = DummyStatus()
    render_calls: list[bool] = []
    monkeypatch.setattr(app, "query_one", lambda _selector, _klass=None: status)
    monkeypatch.setattr(app, "_render_results", lambda: render_calls.append(True))

    app._apply_search_results(1, "alpha", [1, 2], [0.6, 0.4])

    assert app.result_indices == [0]
    assert app.result_scores == [0.9]
    assert render_calls == []
    assert status.messages == []
