"""Tests for indexing exceptions."""

from app.exceptions.base import MemoryServiceError
from app.exceptions.indexing_exceptions import (
    HTTP_STATUS_BAD_GATEWAY,
    HTTP_STATUS_SERVICE_UNAVAILABLE,
    EmbeddingAnomalyError,
    EmbeddingNotConfiguredError,
    EmbeddingPermanentError,
    EmbeddingRateLimitedError,
    EmbeddingTransientError,
)


class TestEmbeddingNotConfiguredError:
    def test_inherits_from_memory_service_error(self) -> None:
        exc = EmbeddingNotConfiguredError()
        assert isinstance(exc, MemoryServiceError)

    def test_has_correct_code(self) -> None:
        exc = EmbeddingNotConfiguredError()
        assert exc.code == "embedding_not_configured"

    def test_has_correct_status_code(self) -> None:
        exc = EmbeddingNotConfiguredError()
        assert exc.status_code == HTTP_STATUS_SERVICE_UNAVAILABLE
        assert exc.status_code == 503


class TestEmbeddingRateLimitedError:
    def test_inherits_from_memory_service_error(self) -> None:
        exc = EmbeddingRateLimitedError()
        assert isinstance(exc, MemoryServiceError)

    def test_has_correct_code(self) -> None:
        exc = EmbeddingRateLimitedError()
        assert exc.code == "embedding_rate_limited"

    def test_has_correct_status_code(self) -> None:
        exc = EmbeddingRateLimitedError()
        assert exc.status_code == HTTP_STATUS_SERVICE_UNAVAILABLE
        assert exc.status_code == 503


class TestEmbeddingTransientError:
    def test_inherits_from_memory_service_error(self) -> None:
        exc = EmbeddingTransientError()
        assert isinstance(exc, MemoryServiceError)

    def test_has_correct_code(self) -> None:
        exc = EmbeddingTransientError()
        assert exc.code == "embedding_transient"

    def test_has_correct_status_code(self) -> None:
        exc = EmbeddingTransientError()
        assert exc.status_code == HTTP_STATUS_SERVICE_UNAVAILABLE
        assert exc.status_code == 503


class TestEmbeddingPermanentError:
    def test_inherits_from_memory_service_error(self) -> None:
        exc = EmbeddingPermanentError()
        assert isinstance(exc, MemoryServiceError)

    def test_has_correct_code(self) -> None:
        exc = EmbeddingPermanentError()
        assert exc.code == "embedding_permanent"

    def test_has_correct_status_code(self) -> None:
        exc = EmbeddingPermanentError()
        assert exc.status_code == HTTP_STATUS_BAD_GATEWAY
        assert exc.status_code == 502


class TestEmbeddingAnomalyError:
    def test_inherits_from_memory_service_error(self) -> None:
        exc = EmbeddingAnomalyError()
        assert isinstance(exc, MemoryServiceError)

    def test_has_correct_code(self) -> None:
        exc = EmbeddingAnomalyError()
        assert exc.code == "embedding_anomaly"

    def test_has_correct_status_code(self) -> None:
        exc = EmbeddingAnomalyError()
        assert exc.status_code == HTTP_STATUS_BAD_GATEWAY
        assert exc.status_code == 502

    def test_is_dimension_mismatch_default_false(self) -> None:
        exc = EmbeddingAnomalyError()
        assert exc.is_dimension_mismatch is False

    def test_is_dimension_mismatch_true(self) -> None:
        exc = EmbeddingAnomalyError(is_dimension_mismatch=True)
        assert exc.is_dimension_mismatch is True

    def test_is_dimension_mismatch_false_explicit(self) -> None:
        exc = EmbeddingAnomalyError(is_dimension_mismatch=False)
        assert exc.is_dimension_mismatch is False
