"""Vertex AI embedding client: the only module that imports google.genai."""

import asyncio
import time
from collections.abc import Awaitable, Callable

import httpx
import structlog
from app.config import Settings
from app.exceptions.indexing_exceptions import (
    EmbeddingAnomalyError,
    EmbeddingNotConfiguredError,
    EmbeddingPermanentError,
    EmbeddingRateLimitedError,
    EmbeddingTransientError,
)
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception_type,
    wait_random,
)

HTTP_STATUS_TOO_MANY_REQUESTS = 429
HTTP_STATUS_SERVER_ERROR_MIN = 500
DOCUMENT_TASK_TYPE = "RETRIEVAL_DOCUMENT"
QUERY_TASK_TYPE = "RETRIEVAL_QUERY"
RETRY_WAIT_MIN_SECONDS = 0.2
RETRY_WAIT_MAX_SECONDS = 1.0
MILLISECONDS_PER_SECOND = 1000

logger = structlog.get_logger()

Clock = Callable[[], float]
Sleeper = Callable[[float], Awaitable[None]]


def _reject_blank_texts(texts: list[str]) -> None:
    if any(not text.strip() for text in texts):
        raise EmbeddingPermanentError("Embedding input must be non-empty text.")


def _classify_api_error(error: genai_errors.APIError) -> Exception:
    if error.code == HTTP_STATUS_TOO_MANY_REQUESTS:
        return EmbeddingRateLimitedError()
    if error.code >= HTTP_STATUS_SERVER_ERROR_MIN:
        return EmbeddingTransientError()
    return EmbeddingPermanentError()


class EmbeddingClient:
    def __init__(
        self,
        api_key: str,
        model_name: str,
        dim: int,
        timeout_seconds: float,
        transient_retries: int,
        *,
        is_adc: bool = False,
        project: str = "",
        location: str = "global",
        clock: Clock = time.monotonic,
        sleep: Sleeper = asyncio.sleep,
    ) -> None:
        if not api_key.strip() and not is_adc:
            raise EmbeddingNotConfiguredError()
        self._api_key = api_key
        self._is_adc = is_adc
        self._project = project
        self._location = location
        self._model_name = model_name
        self._dim = dim
        self._timeout_seconds = timeout_seconds
        self._transient_retries = transient_retries
        self._clock = clock
        self._sleep = sleep
        self._sdk_client: genai.Client | None = None

    async def embed_documents(
        self, texts: list[str], deadline_monotonic: float | None = None
    ) -> list[list[float]]:
        if not texts:
            return []
        _reject_blank_texts(texts)
        return await self._embed(texts, DOCUMENT_TASK_TYPE, deadline_monotonic)

    async def embed_query(self, text: str) -> list[float]:
        _reject_blank_texts([text])
        vectors = await self._embed([text], QUERY_TASK_TYPE, None)
        return vectors[0]

    def _get_sdk_client(self) -> genai.Client:
        if self._sdk_client is None:
            timeout_ms = int(self._timeout_seconds * MILLISECONDS_PER_SECOND)
            http_options = types.HttpOptions(timeout=timeout_ms)
            if self._is_adc:
                self._sdk_client = genai.Client(
                    vertexai=True,
                    project=self._project or None,
                    location=self._location,
                    http_options=http_options,
                )
            else:
                self._sdk_client = genai.Client(
                    vertexai=True, api_key=self._api_key, http_options=http_options
                )
        return self._sdk_client

    async def _embed(
        self, texts: list[str], task_type: str, deadline_monotonic: float | None
    ) -> list[list[float]]:
        retrying = AsyncRetrying(
            retry=retry_if_exception_type(EmbeddingTransientError),
            wait=wait_random(RETRY_WAIT_MIN_SECONDS, RETRY_WAIT_MAX_SECONDS),
            stop=self._build_stop(deadline_monotonic),
            sleep=self._sleep,
            reraise=True,
        )
        vectors = await retrying(self._request_vectors, texts, task_type)
        self._validate_vectors(vectors, expected_count=len(texts))
        return vectors

    def _build_stop(
        self, deadline_monotonic: float | None
    ) -> Callable[[RetryCallState], bool]:
        max_attempts = self._transient_retries + 1

        def should_stop(retry_state: RetryCallState) -> bool:
            if retry_state.attempt_number >= max_attempts:
                return True
            if deadline_monotonic is None:
                return False
            return self._clock() + retry_state.upcoming_sleep > deadline_monotonic

        return should_stop

    async def _request_vectors(
        self, texts: list[str], task_type: str
    ) -> list[list[float]]:
        config = types.EmbedContentConfig(task_type=task_type)
        try:
            response = await self._get_sdk_client().aio.models.embed_content(
                model=self._model_name, contents=texts, config=config
            )
        except genai_errors.APIError as error:
            logger.warning(
                "embedding_call_failed",
                error_class=type(error).__name__,
                status_code=error.code,
            )
            raise _classify_api_error(error) from error
        except (httpx.TransportError, TimeoutError) as error:
            logger.warning(
                "embedding_call_failed",
                error_class=type(error).__name__,
                status_code=None,
            )
            raise EmbeddingTransientError() from error
        return [list(item.values or []) for item in response.embeddings or []]

    def _validate_vectors(
        self, vectors: list[list[float]], expected_count: int
    ) -> None:
        if len(vectors) != expected_count:
            raise EmbeddingAnomalyError("Embedding count did not match input count.")
        if any(len(vector) != self._dim for vector in vectors):
            raise EmbeddingAnomalyError(
                "Embedding dimension did not match configuration.",
                is_dimension_mismatch=True,
            )


def build_embedding_client(settings: Settings) -> EmbeddingClient | None:
    if not settings.embedding_api_key.strip() and not settings.is_vertex_adc_enabled:
        return None
    return EmbeddingClient(
        api_key=settings.embedding_api_key,
        is_adc=settings.is_vertex_adc_enabled,
        project=settings.vertex_project,
        location=settings.vertex_location,
        model_name=settings.embedding_model_name,
        dim=settings.embedding_dim,
        timeout_seconds=settings.embedding_client_timeout_seconds,
        transient_retries=settings.embedding_transient_retries,
    )
