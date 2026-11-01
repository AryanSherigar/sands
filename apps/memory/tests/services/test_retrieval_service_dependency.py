"""get_retrieval_service wires the pool, the settings and the query embedder."""

import pytest
from app.config import Settings
from app.integrations.embedding_client import EmbeddingClient
from app.services import retrieval_service
from app.services.retrieval_service import RetrievalService, get_retrieval_service


@pytest.fixture(autouse=True)
def _reset_embedder_cache() -> None:
    retrieval_service._get_query_embedder.cache_clear()
    yield
    retrieval_service._get_query_embedder.cache_clear()


def wire(monkeypatch: pytest.MonkeyPatch, api_key: str) -> RetrievalService:
    settings = Settings(embedding_api_key=api_key)
    monkeypatch.setattr(retrieval_service, "get_pool", lambda: "pool")
    monkeypatch.setattr(retrieval_service, "get_settings", lambda: settings)
    return get_retrieval_service()


def test_without_an_api_key_the_service_has_no_query_embedder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = wire(monkeypatch, "")

    assert service._query_embedder is None
    assert service._pool == "pool"


def test_with_an_api_key_the_query_embedder_is_the_client_embed_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = wire(monkeypatch, "test-key")

    embedder = service._query_embedder
    assert isinstance(embedder.__self__, EmbeddingClient)
    assert embedder.__func__ is EmbeddingClient.embed_query
