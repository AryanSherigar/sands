"""Tests for app.integrations.embedding_client; HTTP is mocked with respx."""

import json
from collections.abc import Iterator

import httpx
import pytest
import respx
import structlog
from app.config import Settings
from app.exceptions.indexing_exceptions import (
    EmbeddingAnomalyError,
    EmbeddingNotConfiguredError,
    EmbeddingPermanentError,
    EmbeddingRateLimitedError,
    EmbeddingTransientError,
)
from app.integrations.embedding_client import (
    EmbeddingClient,
    build_embedding_client,
)

TEST_DIM = 3
TEST_MODEL = "text-embedding-005"
TEST_TIMEOUT_SECONDS = 5
PREDICT_URL_PATTERN = r"^https://aiplatform\.googleapis\.com/.*:predict$"
INPUT_CANARY = "CANARY-INPUT-TEXT"
PROVIDER_CANARY = "CANARY-PROVIDER-BODY"
DOCUMENT_TASK = "RETRIEVAL_DOCUMENT"
QUERY_TASK = "RETRIEVAL_QUERY"
FAR_FUTURE = 1_000_000.0


class FakeClock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


class RecordingSleep:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


def _vector(seed: float) -> list[float]:
    return [seed, seed + 0.1, seed + 0.2]


def _ok_response(vectors: list[list[float]]) -> httpx.Response:
    predictions = [{"embeddings": {"values": values}} for values in vectors]
    return httpx.Response(200, json={"predictions": predictions})


def _error_response(status_code: int) -> httpx.Response:
    body = {"error": {"code": status_code, "message": PROVIDER_CANARY}}
    return httpx.Response(status_code, json=body)


def _sent_bodies(route: respx.Route) -> list[dict[str, object]]:
    return [json.loads(call.request.content) for call in route.calls]


def _sent_task_types(route: respx.Route) -> list[str]:
    body = _sent_bodies(route)[0]
    instances = body["instances"]
    assert isinstance(instances, list)
    return [instance["task_type"] for instance in instances]


@pytest.fixture
def predict_route() -> Iterator[respx.Route]:
    with respx.mock(assert_all_called=False) as mock:
        yield mock.post(url__regex=PREDICT_URL_PATTERN)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def sleeper() -> RecordingSleep:
    return RecordingSleep()


@pytest.fixture
def client(clock: FakeClock, sleeper: RecordingSleep) -> EmbeddingClient:
    return EmbeddingClient(
        api_key="test-key",
        model_name=TEST_MODEL,
        dim=TEST_DIM,
        timeout_seconds=TEST_TIMEOUT_SECONDS,
        transient_retries=1,
        clock=clock,
        sleep=sleeper,
    )


async def test_embed_documents_returns_vectors_in_order(
    client: EmbeddingClient, predict_route: respx.Route
) -> None:
    predict_route.mock(return_value=_ok_response([_vector(1.0), _vector(2.0)]))

    vectors = await client.embed_documents(["first", "second"])

    assert vectors == [_vector(1.0), _vector(2.0)]
    assert predict_route.call_count == 1


async def test_embed_documents_sends_document_task_type_and_texts(
    client: EmbeddingClient, predict_route: respx.Route
) -> None:
    predict_route.mock(return_value=_ok_response([_vector(1.0), _vector(2.0)]))

    await client.embed_documents(["first", "second"])

    body = _sent_bodies(predict_route)[0]
    assert _sent_task_types(predict_route) == [DOCUMENT_TASK, DOCUMENT_TASK]
    assert [item["content"] for item in body["instances"]] == ["first", "second"]  # type: ignore[index, union-attr]


async def test_embed_documents_does_not_override_output_dimensionality(
    client: EmbeddingClient, predict_route: respx.Route
) -> None:
    predict_route.mock(return_value=_ok_response([_vector(1.0)]))

    await client.embed_documents(["only"])

    body = _sent_bodies(predict_route)[0]
    assert "outputDimensionality" not in json.dumps(body)


async def test_embed_query_uses_query_task_type(
    client: EmbeddingClient, predict_route: respx.Route
) -> None:
    predict_route.mock(return_value=_ok_response([_vector(3.0)]))

    vector = await client.embed_query("where is the key")

    assert vector == _vector(3.0)
    assert _sent_task_types(predict_route) == [QUERY_TASK]


async def test_transient_5xx_once_then_success_makes_two_requests(
    client: EmbeddingClient, predict_route: respx.Route, sleeper: RecordingSleep
) -> None:
    predict_route.mock(side_effect=[_error_response(503), _ok_response([_vector(1.0)])])

    vectors = await client.embed_documents(["text"])

    assert vectors == [_vector(1.0)]
    assert predict_route.call_count == 2
    assert len(sleeper.delays) == 1
    assert 0.2 <= sleeper.delays[0] <= 1.0


async def test_transient_5xx_twice_raises_transient_after_two_requests(
    client: EmbeddingClient, predict_route: respx.Route
) -> None:
    predict_route.mock(return_value=_error_response(500))

    with pytest.raises(EmbeddingTransientError):
        await client.embed_documents(["text"])

    assert predict_route.call_count == 2


async def test_zero_retries_makes_single_request(
    predict_route: respx.Route, sleeper: RecordingSleep
) -> None:
    no_retry_client = EmbeddingClient(
        api_key="test-key",
        model_name=TEST_MODEL,
        dim=TEST_DIM,
        timeout_seconds=TEST_TIMEOUT_SECONDS,
        transient_retries=0,
        sleep=sleeper,
    )
    predict_route.mock(return_value=_error_response(502))

    with pytest.raises(EmbeddingTransientError):
        await no_retry_client.embed_documents(["text"])

    assert predict_route.call_count == 1


async def test_rate_limit_429_is_not_retried(
    client: EmbeddingClient, predict_route: respx.Route
) -> None:
    predict_route.mock(return_value=_error_response(429))

    with pytest.raises(EmbeddingRateLimitedError):
        await client.embed_documents(["text"])

    assert predict_route.call_count == 1


async def test_client_error_400_is_permanent_and_not_retried(
    client: EmbeddingClient, predict_route: respx.Route
) -> None:
    predict_route.mock(return_value=_error_response(400))

    with pytest.raises(EmbeddingPermanentError):
        await client.embed_documents(["text"])

    assert predict_route.call_count == 1


async def test_auth_error_403_is_permanent(
    client: EmbeddingClient, predict_route: respx.Route
) -> None:
    predict_route.mock(return_value=_error_response(403))

    with pytest.raises(EmbeddingPermanentError):
        await client.embed_documents(["text"])

    assert predict_route.call_count == 1


async def test_timeout_is_transient_and_retried(
    client: EmbeddingClient, predict_route: respx.Route
) -> None:
    predict_route.mock(side_effect=httpx.ReadTimeout("slow"))

    with pytest.raises(EmbeddingTransientError):
        await client.embed_documents(["text"])

    assert predict_route.call_count == 2


async def test_connection_error_is_transient_and_recovers(
    client: EmbeddingClient, predict_route: respx.Route
) -> None:
    predict_route.mock(
        side_effect=[httpx.ConnectError("down"), _ok_response([_vector(1.0)])]
    )

    vectors = await client.embed_documents(["text"])

    assert vectors == [_vector(1.0)]
    assert predict_route.call_count == 2


async def test_wrong_vector_count_is_anomaly_without_dimension_flag(
    client: EmbeddingClient, predict_route: respx.Route
) -> None:
    predict_route.mock(return_value=_ok_response([_vector(1.0)]))

    with pytest.raises(EmbeddingAnomalyError) as error_info:
        await client.embed_documents(["first", "second"])

    assert error_info.value.is_dimension_mismatch is False
    assert predict_route.call_count == 1


async def test_wrong_dimension_is_anomaly_with_dimension_flag(
    client: EmbeddingClient, predict_route: respx.Route
) -> None:
    predict_route.mock(return_value=_ok_response([_vector(1.0), [0.1, 0.2]]))

    with pytest.raises(EmbeddingAnomalyError) as error_info:
        await client.embed_documents(["first", "second"])

    assert error_info.value.is_dimension_mismatch is True
    assert predict_route.call_count == 1


async def test_query_wrong_dimension_is_anomaly(
    client: EmbeddingClient, predict_route: respx.Route
) -> None:
    predict_route.mock(return_value=_ok_response([[0.1]]))

    with pytest.raises(EmbeddingAnomalyError) as error_info:
        await client.embed_query("query")

    assert error_info.value.is_dimension_mismatch is True


async def test_empty_list_returns_empty_without_request(
    client: EmbeddingClient, predict_route: respx.Route
) -> None:
    assert await client.embed_documents([]) == []
    assert predict_route.call_count == 0


@pytest.mark.parametrize("bad_text", ["", "   ", "\n\t"])
async def test_blank_document_is_permanent_without_request(
    client: EmbeddingClient, predict_route: respx.Route, bad_text: str
) -> None:
    with pytest.raises(EmbeddingPermanentError):
        await client.embed_documents(["fine", bad_text])

    assert predict_route.call_count == 0


async def test_blank_query_is_permanent_without_request(
    client: EmbeddingClient, predict_route: respx.Route
) -> None:
    with pytest.raises(EmbeddingPermanentError):
        await client.embed_query("  ")

    assert predict_route.call_count == 0


async def test_deadline_already_passed_skips_retry(
    client: EmbeddingClient,
    predict_route: respx.Route,
    clock: FakeClock,
    sleeper: RecordingSleep,
) -> None:
    clock.now = 500.0
    predict_route.mock(return_value=_error_response(503))

    with pytest.raises(EmbeddingTransientError):
        await client.embed_documents(["text"], deadline_monotonic=100.0)

    assert predict_route.call_count == 1
    assert sleeper.delays == []


async def test_retry_sleep_that_would_cross_deadline_is_skipped(
    client: EmbeddingClient, predict_route: respx.Route, clock: FakeClock
) -> None:
    clock.now = 10.0
    predict_route.mock(return_value=_error_response(503))

    with pytest.raises(EmbeddingTransientError):
        await client.embed_documents(["text"], deadline_monotonic=10.05)

    assert predict_route.call_count == 1


async def test_retry_happens_when_deadline_has_room(
    client: EmbeddingClient, predict_route: respx.Route
) -> None:
    predict_route.mock(side_effect=[_error_response(503), _ok_response([_vector(1.0)])])

    vectors = await client.embed_documents(["text"], deadline_monotonic=FAR_FUTURE)

    assert vectors == [_vector(1.0)]
    assert predict_route.call_count == 2


def test_constructor_without_api_key_raises_not_configured() -> None:
    with pytest.raises(EmbeddingNotConfiguredError):
        EmbeddingClient(
            api_key="",
            model_name=TEST_MODEL,
            dim=TEST_DIM,
            timeout_seconds=TEST_TIMEOUT_SECONDS,
            transient_retries=1,
        )


def test_build_helper_returns_none_when_key_is_empty() -> None:
    assert build_embedding_client(Settings(embedding_api_key="")) is None


def test_build_helper_maps_settings_to_client() -> None:
    settings = Settings(
        embedding_api_key="test-key", embedding_dim=TEST_DIM, embedding_model_name="m"
    )

    built = build_embedding_client(settings)

    assert isinstance(built, EmbeddingClient)


def test_adc_client_needs_no_api_key() -> None:
    client = EmbeddingClient(
        api_key="",
        model_name=TEST_MODEL,
        dim=TEST_DIM,
        timeout_seconds=TEST_TIMEOUT_SECONDS,
        transient_retries=1,
        is_adc=True,
    )

    assert isinstance(client, EmbeddingClient)


def test_build_helper_builds_a_client_for_adc_without_a_key() -> None:
    settings = Settings(embedding_api_key="", is_vertex_adc_enabled=True)

    assert isinstance(build_embedding_client(settings), EmbeddingClient)


def test_adc_client_authenticates_with_project_and_location_not_a_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "app.integrations.embedding_client.genai.Client",
        lambda **kwargs: captured.update(kwargs),
    )
    client = EmbeddingClient(
        api_key="ignored-key",
        model_name=TEST_MODEL,
        dim=TEST_DIM,
        timeout_seconds=TEST_TIMEOUT_SECONDS,
        transient_retries=1,
        is_adc=True,
        project="my-project",
        location="global",
    )

    client._get_sdk_client()

    assert captured["project"] == "my-project"
    assert captured["location"] == "global"
    assert "api_key" not in captured


async def test_construction_does_not_build_sdk_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_on_construction(*args: object, **kwargs: object) -> None:
        raise AssertionError("SDK client built eagerly")

    monkeypatch.setattr(
        "app.integrations.embedding_client.genai.Client", fail_on_construction
    )

    EmbeddingClient(
        api_key="test-key",
        model_name=TEST_MODEL,
        dim=TEST_DIM,
        timeout_seconds=TEST_TIMEOUT_SECONDS,
        transient_retries=1,
    )


@pytest.mark.parametrize(
    "response",
    [
        _error_response(400),
        _error_response(429),
        _error_response(503),
        _ok_response([[0.1]]),
    ],
)
async def test_errors_and_logs_never_contain_input_or_provider_text(
    client: EmbeddingClient, predict_route: respx.Route, response: httpx.Response
) -> None:
    predict_route.mock(return_value=response)

    with (
        structlog.testing.capture_logs() as captured_logs,
        pytest.raises(Exception) as error_info,
    ):
        await client.embed_documents([INPUT_CANARY])

    rendered = f"{error_info.value!s} {error_info.value!r} {captured_logs!r}"
    assert INPUT_CANARY not in rendered
    assert PROVIDER_CANARY not in rendered


async def test_transport_exception_text_does_not_leak(
    client: EmbeddingClient, predict_route: respx.Route
) -> None:
    predict_route.mock(side_effect=httpx.ReadTimeout(PROVIDER_CANARY))

    with (
        structlog.testing.capture_logs() as captured_logs,
        pytest.raises(EmbeddingTransientError) as error_info,
    ):
        await client.embed_documents([INPUT_CANARY])

    rendered = f"{error_info.value!s} {error_info.value!r} {captured_logs!r}"
    assert PROVIDER_CANARY not in rendered
    assert INPUT_CANARY not in rendered


async def test_failure_is_logged_with_class_and_status_only(
    client: EmbeddingClient, predict_route: respx.Route
) -> None:
    predict_route.mock(return_value=_error_response(400))

    with (
        structlog.testing.capture_logs() as captured_logs,
        pytest.raises(EmbeddingPermanentError),
    ):
        await client.embed_documents(["text"])

    assert captured_logs
    assert captured_logs[0]["error_class"] == "ClientError"
    assert captured_logs[0]["status_code"] == 400
