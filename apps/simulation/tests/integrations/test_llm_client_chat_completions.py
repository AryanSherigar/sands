"""Chat Completions protocol for the intent, speech and stance provider clients."""

import json

import httpx
import pytest
import structlog.testing
from app.config import Settings
from app.integrations.llm_client import (
    CHAT_COMPLETIONS_REASONING_HEADROOM_TOKENS,
    IntentProviderClient,
    SpeechProviderClient,
    StanceProviderClient,
)
from app.models.battle_intelligence import IntentKind
from app.models.speech_grading import MoodBriefing, SpeechBriefing
from app.models.stance import StanceBriefing, StanceMenuItem
from strategy_contracts.battle_speech import (
    ArmyMood,
    CrowdMood,
    ExhaustionBucket,
    MoraleBucket,
    PayBucket,
)
from tests.integrations.test_llm_client import sample_briefing

PROVIDER_URL = "https://api.meta.ai/v1/chat/completions"


def chat_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "llm_provider_protocol": "chat_completions",
        "llm_provider_reasoning_effort": "minimal",
        "intent_provider_enabled": True,
        "intent_provider_url": PROVIDER_URL,
        "intent_provider_api_key": "test-only",
        "intent_provider_model": "muse-spark-1.3",
        "speech_provider_enabled": True,
        "speech_provider_url": PROVIDER_URL,
        "speech_provider_api_key": "test-only",
        "speech_provider_model": "muse-spark-1.3",
        "stance_provider_enabled": True,
        "stance_provider_url": PROVIDER_URL,
        "stance_provider_api_key": "test-only",
        "stance_provider_model": "muse-spark-1.3",
    }
    return Settings(**{**values, **overrides})


def completion(answer: object, finish_reason: str = "stop") -> httpx.Response:
    content = answer if isinstance(answer, str) else json.dumps(answer)
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "finish_reason": finish_reason,
                    "message": {"role": "assistant", "content": content},
                }
            ]
        },
    )


def recording_transport(
    response: httpx.Response, seen: list[httpx.Request]
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return response

    return httpx.MockTransport(handler)


def stance_briefing() -> StanceBriefing:
    return StanceBriefing(
        leader_name="Mira",
        trait_notes=["Warlike: eager for a fight"],
        ambitions=["Win the crown"],
        memories=[],
        opinions=[],
        current_option_id=None,
        menu=[
            StanceMenuItem(id=item, name=item.title(), description="a stance")
            for item in ("expand", "rebuild", "turtle")
        ],
    )


def speech_briefing() -> SpeechBriefing:
    return SpeechBriefing(
        talks=["We hold the line."],
        ruler_name="Valdren",
        ruler_trait_notes=["Honorable: keeps their word"],
        ruler_ambitions=["Peace"],
        troop_count=900,
        army_morale=60,
        army_fatigue=10,
        unpaid_turns=0,
    )


async def test_intent_uses_chat_envelope_and_returns_the_kind() -> None:
    seen: list[httpx.Request] = []
    client = IntentProviderClient(
        recording_transport(completion({"kind": "delay"}), seen)
    )

    result = await client.generate_intent(chat_settings(), sample_briefing())

    body = json.loads(seen[0].content)
    assert result == IntentKind.DELAY
    assert seen[0].headers["authorization"] == "Bearer test-only"
    assert body["model"] == "muse-spark-1.3"
    assert body["reasoning_effort"] == "minimal"
    assert body["max_completion_tokens"] == (
        256 + CHAT_COMPLETIONS_REASONING_HEADROOM_TOKENS
    )
    assert [message["role"] for message in body["messages"]] == ["system", "user"]
    assert json.loads(body["messages"][1]["content"])["faction_id"]
    schema = body["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["kind"]["enum"] == [item.value for item in IntentKind]
    assert "briefing" not in body


async def test_speech_returns_rubric_scores() -> None:
    seen: list[httpx.Request] = []
    answer = {"addresses_fears": 4, "fits_ruler_character": 3, "promises_made": 1}
    client = SpeechProviderClient(recording_transport(completion(answer), seen))

    result = await client.grade_speech(chat_settings(), speech_briefing())

    body = json.loads(seen[0].content)
    assert result.addresses_fears == 4
    assert body["response_format"]["json_schema"]["schema"]["required"] == [
        "addresses_fears",
        "fits_ruler_character",
        "promises_made",
    ]


async def test_speech_mood_uses_chat_envelope_and_returns_a_menu_reaction() -> None:
    seen: list[httpx.Request] = []
    answer = {"mood": "protest", "intensity": 3}
    client = SpeechProviderClient(recording_transport(completion(answer), seen))
    briefing = MoodBriefing(
        talks=["Pay is coming."],
        ruler_name="Valdren",
        ruler_trait_notes=[],
        army_mood=ArmyMood(
            morale=MoraleBucket.BROKEN,
            exhaustion=ExhaustionBucket.SPENT,
            pay=PayBucket.UNPAID,
        ),
    )

    result = await client.react_to_talk(chat_settings(), briefing)

    body = json.loads(seen[0].content)
    assert (result.mood, result.intensity) == (CrowdMood.PROTEST, 3)
    assert [message["role"] for message in body["messages"]] == ["system", "user"]
    schema = body["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["mood"]["enum"] == [item.value for item in CrowdMood]
    assert json.loads(body["messages"][1]["content"])["talks"] == ["Pay is coming."]


async def test_stance_returns_a_menu_option() -> None:
    seen: list[httpx.Request] = []
    client = StanceProviderClient(
        recording_transport(completion({"option_id": "turtle"}), seen)
    )

    result = await client.pick_stance(chat_settings(), stance_briefing())

    body = json.loads(seen[0].content)
    assert result.option_id == "turtle"
    schema = body["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["option_id"]["enum"] == ["expand", "rebuild", "turtle"]


async def test_unset_reasoning_effort_is_not_sent() -> None:
    seen: list[httpx.Request] = []
    client = StanceProviderClient(
        recording_transport(completion({"option_id": "turtle"}), seen)
    )

    await client.pick_stance(
        chat_settings(llm_provider_reasoning_effort=""), stance_briefing()
    )

    assert "reasoning_effort" not in json.loads(seen[0].content)


@pytest.mark.parametrize(
    "response",
    [
        completion("not json"),
        completion({"option_id": "turtle", "extra": "x"}),
        completion({"option_id": "turtle"}, finish_reason="length"),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={}),
        httpx.Response(500),
    ],
)
async def test_bad_chat_answers_raise(response: httpx.Response) -> None:
    client = StanceProviderClient(httpx.MockTransport(lambda request: response))

    with pytest.raises((ValueError, httpx.HTTPStatusError)):
        await client.pick_stance(chat_settings(), stance_briefing())


async def test_custom_protocol_is_the_default() -> None:
    seen: list[httpx.Request] = []
    client = StanceProviderClient(
        recording_transport(httpx.Response(200, json={"option_id": "turtle"}), seen)
    )

    await client.pick_stance(
        chat_settings(llm_provider_protocol="custom"), stance_briefing()
    )

    assert "briefing" in json.loads(seen[0].content)


def completion_with_usage(answer: object) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": json.dumps(answer)},
                }
            ],
            "usage": {
                "prompt_tokens": 300,
                "completion_tokens": 40,
                "prompt_tokens_details": {"cached_tokens": 200},
            },
        },
    )


async def test_each_provider_logs_token_counts_from_the_envelope() -> None:
    cases = [
        ("intent", {"kind": "delay"}),
        ("stance", {"option_id": "turtle"}),
        (
            "speech",
            {"addresses_fears": 3, "fits_ruler_character": 3, "promises_made": 3},
        ),
    ]
    with structlog.testing.capture_logs() as logs:
        for provider, answer in cases:
            seen: list[httpx.Request] = []
            transport = recording_transport(completion_with_usage(answer), seen)
            if provider == "intent":
                await IntentProviderClient(transport).generate_intent(
                    chat_settings(), sample_briefing()
                )
            elif provider == "stance":
                await StanceProviderClient(transport).pick_stance(
                    chat_settings(), stance_briefing()
                )
            else:
                await SpeechProviderClient(transport).grade_speech(
                    chat_settings(), speech_briefing()
                )

    events = [entry for entry in logs if entry["event"] == "provider_model_usage"]
    assert [entry["provider"] for entry in events] == ["intent", "stance", "speech"]
    for entry in events:
        assert (
            entry["prompt_tokens"],
            entry["completion_tokens"],
            entry["cached_tokens"],
        ) == (300, 40, 200)


async def test_usage_log_carries_no_prompt_or_answer_text() -> None:
    seen: list[httpx.Request] = []
    transport = recording_transport(
        completion_with_usage({"option_id": "turtle"}), seen
    )

    with structlog.testing.capture_logs() as logs:
        await StanceProviderClient(transport).pick_stance(
            chat_settings(), stance_briefing()
        )

    logged = str(logs)
    assert "Mira" not in logged
    assert "turtle" not in logged


async def test_usage_is_logged_even_when_the_answer_is_unusable() -> None:
    seen: list[httpx.Request] = []
    transport = recording_transport(completion_with_usage({"option_id": 7}), seen)

    with structlog.testing.capture_logs() as logs, pytest.raises(ValueError):
        await StanceProviderClient(transport).pick_stance(
            chat_settings(), stance_briefing()
        )

    assert any(entry["event"] == "provider_model_usage" for entry in logs)
