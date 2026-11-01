import json

import httpx
import pytest
from app.config import Settings
from app.integrations.llm_client import SpeechProviderClient
from app.models.speech_grading import SpeechBriefing
from pydantic import ValidationError
from strategy_contracts.scene import SpeechRubric

ANSWER = {"addresses_fears": 4, "fits_ruler_character": 5, "promises_made": 1}


def briefing() -> SpeechBriefing:
    return SpeechBriefing(
        speech_text="We hold the line.",
        ruler_name="Valdren",
        ruler_trait_notes=["Honorable: keeps their word"],
        ruler_ambitions=["Peace"],
        troop_count=900,
        army_morale=60,
        army_fatigue=10,
        unpaid_turns=0,
    )


def settings() -> Settings:
    return Settings(
        speech_provider_enabled=True,
        speech_provider_url="https://provider.invalid/speech",
        speech_provider_api_key="test-only",
        speech_provider_model="fake-model",
    )


def client_returning(response: httpx.Response) -> SpeechProviderClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        return response

    return SpeechProviderClient(httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_client_sends_the_rulers_traits_and_returns_rubric_scores() -> None:
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=ANSWER)

    client = SpeechProviderClient(httpx.MockTransport(handler))
    answer = await client.grade_speech(settings(), briefing())

    body = json.loads(seen[0].content)
    assert body["briefing"]["ruler_trait_notes"] == ["Honorable: keeps their word"]
    assert body["response_schema"]["additionalProperties"] is False
    assert answer.as_scores()[SpeechRubric.FITS_RULER_CHARACTER] == 5


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b""),
        httpx.Response(200, content=b"x" * 5000),
        httpx.Response(200, json=ANSWER | {"extra": 1}),
        httpx.Response(200, json=ANSWER | {"promises_made": 9}),
        httpx.Response(500),
    ],
)
async def test_client_rejects_malformed_or_failed_answers(
    response: httpx.Response,
) -> None:
    with pytest.raises((ValueError, ValidationError, httpx.HTTPError)):
        await client_returning(response).grade_speech(settings(), briefing())


@pytest.mark.asyncio
async def test_client_requires_credentials() -> None:
    with pytest.raises(ValueError):
        await client_returning(httpx.Response(200, json=ANSWER)).grade_speech(
            Settings(), briefing()
        )
