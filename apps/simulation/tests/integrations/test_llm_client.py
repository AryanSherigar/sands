import asyncio
import json

import httpx
import pytest
from app.config import Settings
from app.engine.battles.views import intent_briefing
from app.integrations.llm_client import IntentProviderClient
from app.models.battle_intelligence import IntentKind
from app.models.intent_briefing import IntentBriefing
from tests.engine.battles.builders import DEFENDER, battle_fixture, start_battle


def sample_briefing() -> IntentBriefing:
    world, scenario = battle_fixture()
    start_battle(world, scenario)
    return intent_briefing(world, world.battles[0].id, DEFENDER, scenario)


def settings() -> Settings:
    return Settings(
        intent_provider_enabled=True,
        intent_provider_url="https://provider.invalid/intent",
        intent_provider_api_key="test-only",
        intent_provider_model="fake-model",
    )


@pytest.mark.asyncio
async def test_client_accepts_only_a_fixed_menu_answer() -> None:
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"kind": "press"})

    client = IntentProviderClient(httpx.MockTransport(handler))
    result = await client.generate_intent(settings(), sample_briefing())

    body = json.loads(seen[0].content)
    assert result == IntentKind.PRESS
    assert body["max_output_tokens"] == 256
    assert body["allowed_intents"] == [item.value for item in IntentKind]
    assert seen[0].headers["authorization"] == "Bearer test-only"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        b"Here is my strategy: press hard.",
        b'{"kind":"secret_plan"}',
        b'{"kind":"press","prose":"attack the reserve"}',
        b'{"kind":',
        b'{"refusal":"I cannot help"}',
    ],
)
async def test_client_rejects_untyped_or_incomplete_answers(body: bytes) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    client = IntentProviderClient(transport)

    with pytest.raises((ValueError, json.JSONDecodeError)):
        await client.generate_intent(settings(), sample_briefing())


@pytest.mark.asyncio
async def test_client_bounds_provider_timeout() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.05)
        return httpx.Response(200, json={"kind": "delay"})

    slow_settings = settings().model_copy(
        update={"intent_provider_timeout_seconds": 0.01}
    )
    client = IntentProviderClient(httpx.MockTransport(handler))

    with pytest.raises(TimeoutError):
        await client.generate_intent(slow_settings, sample_briefing())
