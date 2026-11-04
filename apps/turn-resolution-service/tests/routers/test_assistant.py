"""Integration tests for Studio Assistant endpoint POST /v1/studio/assistant."""

import uuid
from collections.abc import AsyncIterator

from app.config import settings
from app.exceptions.turn_exceptions import LlmUnavailableError
from app.integrations import openai_compatible_client
from app.models.assistant import AssistantChatRequest
from app.models.auth import CurrentUser
from app.routers.assistant import chat_with_assistant
from app.services.rate_limit.exemption_service import get_exemption_service
from app.services.rate_limit.quota_service import QuotaService
from app.services.rate_limit.store import get_rate_limit_store
from app.services.rate_limit.stream_lease_service import StreamLeaseService
from google.genai import types
from httpx import AsyncClient


def _make_auth_headers() -> dict[str, str]:
    return {"X-Dev-User-Id": str(uuid.uuid4())}


async def test_assistant_chat_response_uses_configured_ping_interval(
    monkeypatch,
) -> None:
    """[P2-STREAM-3] Without a ping= interval, EventSourceResponse falls back
    to its own default instead of the project's configured keep-alive, which
    the other SSE endpoints (response_streamer.py, session.py) all set."""

    async def fake_stream_chat(
        system_instruction: str,
        contents: list[types.Content],
        timeout_seconds: int,
        max_output_tokens: int = 1500,
        usage_sink: object | None = None,
    ) -> AsyncIterator[str]:
        yield "Hello."

    monkeypatch.setattr(openai_compatible_client, "stream_chat", fake_stream_chat)

    request = AssistantChatRequest(messages=[{"role": "user", "content": "Hi"}])
    user = CurrentUser(user_id=uuid.uuid4(), token_version=1)

    store = get_rate_limit_store()
    response = await chat_with_assistant(
        request,
        user,
        QuotaService(store, get_exemption_service()),
        StreamLeaseService(store),
    )

    assert response.ping_interval == settings.sse_ping_interval_seconds


async def test_assistant_chat_requires_auth(async_client: AsyncClient) -> None:
    payload = {"messages": [{"role": "user", "content": "Help me with lore"}]}
    response = await async_client.post("/v1/studio/assistant", json=payload)
    assert response.status_code == 401


async def test_assistant_chat_streams_chunks_and_done(
    async_client: AsyncClient, monkeypatch
) -> None:
    async def fake_stream_chat(
        system_instruction: str,
        contents: list[types.Content],
        timeout_seconds: int,
        max_output_tokens: int = 1500,
        usage_sink: object | None = None,
    ) -> AsyncIterator[str]:
        yield "Welcome to "
        yield "the forgotten realm."

    monkeypatch.setattr(openai_compatible_client, "stream_chat", fake_stream_chat)

    payload = {
        "messages": [{"role": "user", "content": "Give me world intro"}],
        "draft_context": {
            "title": "Sunken Kingdom",
            "active_section": "lore",
        },
    }
    response = await async_client.post(
        "/v1/studio/assistant",
        json=payload,
        headers=_make_auth_headers(),
    )
    assert response.status_code == 200
    body = response.text
    assert "event: chunk\r\ndata: Welcome to " in body or "data: Welcome to " in body
    assert "event: done\r\ndata: " in body or "done" in body


async def test_assistant_chat_master_mode_uses_systems_designer_persona(
    async_client: AsyncClient, monkeypatch
) -> None:
    captured_instructions: list[str] = []

    async def fake_stream_chat(
        system_instruction: str,
        contents: list[types.Content],
        timeout_seconds: int,
        max_output_tokens: int = 1500,
        usage_sink: object | None = None,
    ) -> AsyncIterator[str]:
        captured_instructions.append(system_instruction)
        yield "Let's add an entity."

    monkeypatch.setattr(openai_compatible_client, "stream_chat", fake_stream_chat)

    payload = {
        "messages": [{"role": "user", "content": "Add a villain entity"}],
        "mode": "master",
        "master_context": {
            "title": "Sunken Kingdom",
            "active_tab": "entities",
            "entities": [
                {
                    "entity_id": str(uuid.uuid4()),
                    "entity_type": "character",
                    "canonical_name": "Hero",
                }
            ],
        },
    }
    response = await async_client.post(
        "/v1/studio/assistant",
        json=payload,
        headers=_make_auth_headers(),
    )
    assert response.status_code == 200
    assert len(captured_instructions) == 1
    instruction = captured_instructions[0]
    assert "game systems designer" in instruction
    assert "Sunken Kingdom" in instruction
    assert "action:entity" in instruction
    assert "action:fact" in instruction
    assert "world-building co-author" not in instruction


async def test_assistant_chat_defaults_to_newbie_mode(
    async_client: AsyncClient, monkeypatch
) -> None:
    captured_instructions: list[str] = []

    async def fake_stream_chat(
        system_instruction: str,
        contents: list[types.Content],
        timeout_seconds: int,
        max_output_tokens: int = 1500,
        usage_sink: object | None = None,
    ) -> AsyncIterator[str]:
        captured_instructions.append(system_instruction)
        yield "Welcome."

    monkeypatch.setattr(openai_compatible_client, "stream_chat", fake_stream_chat)

    payload = {"messages": [{"role": "user", "content": "Hello"}]}
    response = await async_client.post(
        "/v1/studio/assistant",
        json=payload,
        headers=_make_auth_headers(),
    )
    assert response.status_code == 200
    assert "world-building co-author" in captured_instructions[0]
    assert "game systems designer" not in captured_instructions[0]


async def test_assistant_chat_flags_hallucinated_field_in_generated_condition(
    async_client: AsyncClient, monkeypatch
) -> None:
    async def fake_stream_chat(
        system_instruction: str,
        contents: list[types.Content],
        timeout_seconds: int,
        max_output_tokens: int = 1500,
        usage_sink: object | None = None,
    ) -> AsyncIterator[str]:
        yield "Here is a rule:\n```action:condition\n"
        yield (
            '{"label": "Bribe", "narrator_instruction": "Offer a bribe.", '
            '"condition_expression": {"field": "mana", "op": ">=", "value": 10}}\n'
        )
        yield "```"

    monkeypatch.setattr(openai_compatible_client, "stream_chat", fake_stream_chat)

    payload = {
        "messages": [{"role": "user", "content": "Add a bribe condition"}],
        "mode": "master",
        "master_context": {
            "title": "Sunken Kingdom",
            "active_tab": "conditions",
            "state_schema": {"gold": {"type": "number"}},
        },
    }
    response = await async_client.post(
        "/v1/studio/assistant",
        json=payload,
        headers=_make_auth_headers(),
    )
    assert response.status_code == 200
    assert "event: done" in response.text
    assert "block_validation" in response.text
    assert "Unknown field 'mana'" in response.text


async def test_assistant_chat_no_validation_payload_for_valid_condition(
    async_client: AsyncClient, monkeypatch
) -> None:
    async def fake_stream_chat(
        system_instruction: str,
        contents: list[types.Content],
        timeout_seconds: int,
        max_output_tokens: int = 1500,
        usage_sink: object | None = None,
    ) -> AsyncIterator[str]:
        yield "Here is a rule:\n```action:condition\n"
        yield (
            '{"label": "Bribe", "narrator_instruction": "Offer a bribe.", '
            '"condition_expression": {"field": "gold", "op": ">=", "value": 10}}\n'
        )
        yield "```"

    monkeypatch.setattr(openai_compatible_client, "stream_chat", fake_stream_chat)

    payload = {
        "messages": [{"role": "user", "content": "Add a bribe condition"}],
        "mode": "master",
        "master_context": {
            "title": "Sunken Kingdom",
            "active_tab": "conditions",
            "state_schema": {"gold": {"type": "number"}},
        },
    }
    response = await async_client.post(
        "/v1/studio/assistant",
        json=payload,
        headers=_make_auth_headers(),
    )
    assert response.status_code == 200
    assert "block_validation" not in response.text


async def test_assistant_chat_flags_overlong_logline(
    async_client: AsyncClient, monkeypatch
) -> None:
    overlong_logline = "A" * 200

    async def fake_stream_chat(
        system_instruction: str,
        contents: list[types.Content],
        timeout_seconds: int,
        max_output_tokens: int = 1500,
        usage_sink: object | None = None,
    ) -> AsyncIterator[str]:
        yield f"Here you go:\n```action:logline\n{overlong_logline}\n```"

    monkeypatch.setattr(openai_compatible_client, "stream_chat", fake_stream_chat)

    payload = {
        "messages": [{"role": "user", "content": "Give me a logline"}],
        "mode": "master",
        "master_context": {"title": "Sunken Kingdom", "active_tab": "setup"},
    }
    response = await async_client.post(
        "/v1/studio/assistant",
        json=payload,
        headers=_make_auth_headers(),
    )
    assert response.status_code == 200
    assert "block_validation" in response.text
    assert "150-character limit" in response.text


async def test_assistant_chat_does_not_flag_informal_attribute_schema(
    async_client: AsyncClient, monkeypatch
) -> None:
    """attributes_schema shape quirks (a bare type name, a bare initial value)
    are auto-normalized when applied (useMasterActionApplier.ts), so entity
    blocks are never flagged for this — flagging it would be actively
    misleading since Apply will succeed anyway."""

    async def fake_stream_chat(
        system_instruction: str,
        contents: list[types.Content],
        timeout_seconds: int,
        max_output_tokens: int = 1500,
        usage_sink: object | None = None,
    ) -> AsyncIterator[str]:
        yield "Here is a guard:\n```action:entity\n"
        yield (
            '{"entity_type": "character", "canonical_name": "Guard Captain", '
            '"attributes_schema": {"role": "Captain", "age": 34, '
            '"loyalty": "number"}}\n'
        )
        yield "```"

    monkeypatch.setattr(openai_compatible_client, "stream_chat", fake_stream_chat)

    payload = {
        "messages": [{"role": "user", "content": "Add a guard captain"}],
        "mode": "master",
        "master_context": {"title": "Sunken Kingdom", "active_tab": "entities"},
    }
    response = await async_client.post(
        "/v1/studio/assistant",
        json=payload,
        headers=_make_auth_headers(),
    )
    assert response.status_code == 200
    assert "block_validation" not in response.text


async def test_assistant_chat_flags_fact_referencing_unknown_entity(
    async_client: AsyncClient, monkeypatch
) -> None:
    async def fake_stream_chat(
        system_instruction: str,
        contents: list[types.Content],
        timeout_seconds: int,
        max_output_tokens: int = 1500,
        usage_sink: object | None = None,
    ) -> AsyncIterator[str]:
        yield "Here is a fact:\n```action:fact\n"
        yield (
            '{"subject_ref": "goblin_scout", "predicate": "guards", '
            '"object_literal": "the eastern gate"}\n'
        )
        yield "```"

    monkeypatch.setattr(openai_compatible_client, "stream_chat", fake_stream_chat)

    payload = {
        "messages": [{"role": "user", "content": "Add a guarding fact"}],
        "mode": "master",
        "master_context": {"title": "Sunken Kingdom", "active_tab": "facts"},
    }
    response = await async_client.post(
        "/v1/studio/assistant",
        json=payload,
        headers=_make_auth_headers(),
    )
    assert response.status_code == 200
    assert "block_validation" in response.text
    assert "goblin_scout" in response.text


async def test_assistant_chat_allows_fact_referencing_same_reply_temp_id(
    async_client: AsyncClient, monkeypatch
) -> None:
    async def fake_stream_chat(
        system_instruction: str,
        contents: list[types.Content],
        timeout_seconds: int,
        max_output_tokens: int = 1500,
        usage_sink: object | None = None,
    ) -> AsyncIterator[str]:
        yield "Here you go:\n```action:entity\n"
        yield (
            '{"temp_id": "goblin_scout", "entity_type": "character", '
            '"canonical_name": "Goblin Scout"}\n```\n'
        )
        yield "```action:fact\n"
        yield (
            '{"subject_ref": "goblin_scout", "predicate": "guards", '
            '"object_literal": "the eastern gate"}\n'
        )
        yield "```"

    monkeypatch.setattr(openai_compatible_client, "stream_chat", fake_stream_chat)

    payload = {
        "messages": [{"role": "user", "content": "Add a scout and a guarding fact"}],
        "mode": "master",
        "master_context": {"title": "Sunken Kingdom", "active_tab": "facts"},
    }
    response = await async_client.post(
        "/v1/studio/assistant",
        json=payload,
        headers=_make_auth_headers(),
    )
    assert response.status_code == 200
    assert "block_validation" not in response.text


async def test_assistant_chat_handles_llm_unavailable(
    async_client: AsyncClient, monkeypatch
) -> None:
    async def failing_stream_chat(
        system_instruction: str,
        contents: list[types.Content],
        timeout_seconds: int,
        max_output_tokens: int = 1500,
        usage_sink: object | None = None,
    ) -> AsyncIterator[str]:
        raise LlmUnavailableError()
        yield ""

    monkeypatch.setattr(openai_compatible_client, "stream_chat", failing_stream_chat)

    payload = {
        "messages": [{"role": "user", "content": "Hello"}],
    }
    response = await async_client.post(
        "/v1/studio/assistant",
        json=payload,
        headers=_make_auth_headers(),
    )
    assert response.status_code == 200
    assert "event: error" in response.text


async def test_assistant_chat_accepts_scoped_context_and_sends_only_the_tab(
    async_client: AsyncClient, monkeypatch
) -> None:
    captured: dict[str, str] = {}

    async def fake_stream_chat(
        system_instruction: str,
        contents: list[types.Content],
        timeout_seconds: int,
        max_output_tokens: int = 1500,
        usage_sink: object | None = None,
    ) -> AsyncIterator[str]:
        captured["instruction"] = system_instruction
        yield "Sure."

    monkeypatch.setattr(openai_compatible_client, "stream_chat", fake_stream_chat)

    payload = {
        "messages": [{"role": "user", "content": "Tighten this."}],
        "mode": "scoped",
        "scoped_context": {
            "one_line_idea": "A keeper guards a failing light.",
            "tab_kind": "premise",
            "tab_label": "Premise",
            "tab_text": "",
        },
    }
    response = await async_client.post(
        "/v1/studio/assistant", json=payload, headers=_make_auth_headers()
    )

    assert response.status_code == 200
    assert "CURRENT TAB IN STUDIO:" in captured["instruction"]
    assert "A keeper guards a failing light." in captured["instruction"]
    assert "Premise" in captured["instruction"]


async def test_assistant_chat_rejects_unknown_mode(
    async_client: AsyncClient,
) -> None:
    payload = {"messages": [], "mode": "everything"}
    response = await async_client.post(
        "/v1/studio/assistant", json=payload, headers=_make_auth_headers()
    )

    assert response.status_code == 422


async def test_assistant_chat_strategy_mode_flags_unknown_faction_ids(
    async_client: AsyncClient, monkeypatch
) -> None:
    captured: dict[str, str] = {}
    reply = (
        "Try this:\n```action:relation\n"
        '{"faction_a": "north", "faction_b": "ghost", "status": "war"}\n```\n'
    )

    async def fake_stream_chat(
        system_instruction: str,
        contents: list[types.Content],
        timeout_seconds: int,
        max_output_tokens: int = 1500,
        usage_sink: object | None = None,
    ) -> AsyncIterator[str]:
        captured["instruction"] = system_instruction
        yield reply

    monkeypatch.setattr(openai_compatible_client, "stream_chat", fake_stream_chat)

    payload = {
        "messages": [{"role": "user", "content": "Start a war."}],
        "mode": "strategy",
        "strategy_context": {
            "title": "Two Crowns",
            "factions": [{"faction_id": "north", "name": "North"}],
        },
    }
    response = await async_client.post(
        "/v1/studio/assistant", json=payload, headers=_make_auth_headers()
    )

    assert response.status_code == 200
    assert "CURRENT STRATEGY SCENARIO DATA:" in captured["instruction"]
    assert "block_validation" in response.text
    assert "ghost" in response.text


async def test_assistant_chat_strategy_mode_valid_block_has_no_validation(
    async_client: AsyncClient, monkeypatch
) -> None:
    reply = (
        "```action:relation\n"
        '{"faction_a": "north", "faction_b": "south", "status": "peace"}\n```\n'
    )

    async def fake_stream_chat(
        system_instruction: str,
        contents: list[types.Content],
        timeout_seconds: int,
        max_output_tokens: int = 1500,
        usage_sink: object | None = None,
    ) -> AsyncIterator[str]:
        yield reply

    monkeypatch.setattr(openai_compatible_client, "stream_chat", fake_stream_chat)

    payload = {
        "messages": [{"role": "user", "content": "Make peace."}],
        "mode": "strategy",
        "strategy_context": {
            "factions": [
                {"faction_id": "north", "name": "North"},
                {"faction_id": "south", "name": "South"},
            ]
        },
    }
    response = await async_client.post(
        "/v1/studio/assistant", json=payload, headers=_make_auth_headers()
    )

    assert response.status_code == 200
    assert "block_validation" not in response.text
