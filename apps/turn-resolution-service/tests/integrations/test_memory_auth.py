"""Google ID-token auth for memory calls: attach, cache, refresh, degrade."""

import time
from uuid import uuid4

import httpx
import pytest
import respx
from app.config import settings
from app.exceptions.memory_exceptions import MemoryRetrieveError
from app.integrations import memory_auth, memory_client
from app.integrations.memory_auth import IdTokenAuth, MemoryAuthError
from app.models.memory import RetrieveRequest
from google.auth import exceptions as google_auth_exceptions

AUDIENCE = "https://memory.example.test"
PING_URL = f"{AUDIENCE}/ping"
TOKEN_LIFETIME_SECONDS = 3600
EXPIRY_MARGIN_SECONDS = 60


class FakeTokenSource:
    def __init__(self) -> None:
        self.audiences: list[str] = []

    def __call__(self, audience: str) -> str:
        self.audiences.append(audience)
        return f"token-{len(self.audiences)}"


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000_000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture(autouse=True)
def _reset_client_singleton(monkeypatch):
    monkeypatch.setattr(memory_client, "_client", None)
    yield
    monkeypatch.setattr(memory_client, "_client", None)


@pytest.fixture
def source(monkeypatch) -> FakeTokenSource:
    fake = FakeTokenSource()
    monkeypatch.setattr(memory_auth, "fetch_google_id_token", fake)
    monkeypatch.setattr(
        memory_auth, "_expiry_of", lambda token: time.time() + TOKEN_LIFETIME_SECONDS
    )
    return fake


def build_client(auth: httpx.Auth | None) -> httpx.AsyncClient:
    return httpx.AsyncClient(auth=auth)


@pytest.mark.asyncio
async def test_bearer_token_is_attached_with_the_memory_audience(source) -> None:
    with respx.mock as router:
        route = router.get(PING_URL).respond(200)
        async with build_client(IdTokenAuth(AUDIENCE)) as client:
            await client.get(PING_URL)

    assert route.calls[0].request.headers["Authorization"] == "Bearer token-1"
    assert source.audiences == [AUDIENCE]


@pytest.mark.asyncio
async def test_token_is_cached_across_requests(source) -> None:
    with respx.mock as router:
        router.get(PING_URL).respond(200)
        async with build_client(IdTokenAuth(AUDIENCE)) as client:
            await client.get(PING_URL)
            await client.get(PING_URL)

    assert source.audiences == [AUDIENCE]


@pytest.mark.asyncio
async def test_token_is_refreshed_shortly_before_it_expires(monkeypatch) -> None:
    clock = FakeClock()
    monkeypatch.setattr(
        memory_auth, "_expiry_of", lambda token: clock.now + TOKEN_LIFETIME_SECONDS
    )
    source = FakeTokenSource()
    auth = IdTokenAuth(AUDIENCE, fetch_token=source, clock=clock)
    with respx.mock as router:
        router.get(PING_URL).respond(200)
        async with build_client(auth) as client:
            await client.get(PING_URL)
            clock.now += TOKEN_LIFETIME_SECONDS - EXPIRY_MARGIN_SECONDS + 1
            await client.get(PING_URL)

    assert len(source.audiences) == 2


@pytest.mark.asyncio
async def test_a_401_drops_the_cached_token(source) -> None:
    with respx.mock as router:
        router.get(PING_URL).mock(
            side_effect=[httpx.Response(401), httpx.Response(200)]
        )
        async with build_client(IdTokenAuth(AUDIENCE)) as client:
            await client.get(PING_URL)
            await client.get(PING_URL)

    assert len(source.audiences) == 2


@pytest.mark.asyncio
async def test_failed_token_fetch_is_an_http_error(monkeypatch) -> None:
    def broken(audience: str) -> str:
        raise google_auth_exceptions.DefaultCredentialsError("no metadata server")

    monkeypatch.setattr(memory_auth, "fetch_google_id_token", broken)
    with respx.mock as router:
        router.get(PING_URL).respond(200)
        async with build_client(IdTokenAuth(AUDIENCE)) as client:
            with pytest.raises(MemoryAuthError):
                await client.get(PING_URL)

    assert issubclass(MemoryAuthError, httpx.HTTPError)


def test_no_auth_object_when_iam_is_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "is_memory_iam_auth_enabled", False)

    assert memory_auth.build_memory_auth() is None


def test_auth_object_targets_the_memory_url_when_iam_is_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "is_memory_iam_auth_enabled", True)
    monkeypatch.setattr(settings, "memory_url", AUDIENCE)

    auth = memory_auth.build_memory_auth()

    assert isinstance(auth, IdTokenAuth)


def retrieve_request() -> RetrieveRequest:
    return RetrieveRequest.model_construct(playthrough_id=uuid4())


@pytest.mark.asyncio
async def test_client_sends_no_authorization_in_dev_mode(monkeypatch) -> None:
    monkeypatch.setattr(settings, "is_memory_iam_auth_enabled", False)
    monkeypatch.setattr(settings, "memory_url", AUDIENCE)
    with respx.mock as router:
        route = router.post(f"{AUDIENCE}/v1/retrieve").respond(500)
        with pytest.raises(MemoryRetrieveError):
            await memory_client.retrieve(retrieve_request())

    assert "Authorization" not in route.calls[0].request.headers


@pytest.mark.asyncio
async def test_client_sends_the_id_token_in_iam_mode(monkeypatch, source) -> None:
    monkeypatch.setattr(settings, "is_memory_iam_auth_enabled", True)
    monkeypatch.setattr(settings, "memory_url", AUDIENCE)
    with respx.mock as router:
        route = router.post(f"{AUDIENCE}/v1/retrieve").respond(500)
        with pytest.raises(MemoryRetrieveError):
            await memory_client.retrieve(retrieve_request())

    assert route.calls[0].request.headers["Authorization"] == "Bearer token-1"
    assert source.audiences == [AUDIENCE]


@pytest.mark.asyncio
async def test_token_failure_degrades_to_an_unavailable_error(monkeypatch) -> None:
    def broken(audience: str) -> str:
        raise google_auth_exceptions.TransportError("metadata unreachable")

    monkeypatch.setattr(memory_auth, "fetch_google_id_token", broken)
    monkeypatch.setattr(settings, "is_memory_iam_auth_enabled", True)
    monkeypatch.setattr(settings, "memory_url", AUDIENCE)

    with pytest.raises(MemoryRetrieveError) as raised:
        await memory_client.retrieve(retrieve_request())

    assert raised.value.code == "unavailable"


@pytest.mark.asyncio
async def test_a_401_from_memory_surfaces_its_code_not_a_crash(
    monkeypatch, source
) -> None:
    monkeypatch.setattr(settings, "is_memory_iam_auth_enabled", True)
    monkeypatch.setattr(settings, "memory_url", AUDIENCE)
    with respx.mock as router:
        router.post(f"{AUDIENCE}/v1/retrieve").respond(
            401, json={"detail": "x", "code": "invalid_token"}
        )
        with pytest.raises(MemoryRetrieveError) as raised:
            await memory_client.retrieve(retrieve_request())

    assert raised.value.code == "invalid_token"
    assert raised.value.upstream_status == 401
