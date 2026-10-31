"""Unit tests for ruler_backstory_service.py with the text client mocked."""

import uuid
from unittest.mock import AsyncMock

import pytest
from app.integrations import text_gen_client
from app.models.strategy_ruler import RulerBackstoryRequest
from app.services import ruler_backstory_service


def _request(**overrides: object) -> RulerBackstoryRequest:
    values: dict[str, object] = {
        "scenario_id": uuid.uuid4(),
        "faction_id": "valenreach",
        "ruler_name": "King Alden IV",
        "epithet": "Sovereign of the Marches",
        "trait_ids": ["honorable", "cautious"],
        "ambition_ids": ["ambition_peace"],
    }
    return RulerBackstoryRequest(**{**values, **overrides})


def test_prompt_names_the_ruler_epithet_traits_and_ambitions() -> None:
    prompt = ruler_backstory_service.build_backstory_prompt(_request())

    assert "King Alden IV, Sovereign of the Marches of valenreach" in prompt
    assert "honorable, cautious" in prompt
    assert "ambition_peace" in prompt


def test_prompt_falls_back_when_traits_and_ambitions_are_empty() -> None:
    prompt = ruler_backstory_service.build_backstory_prompt(
        _request(epithet=None, trait_ids=[], ambition_ids=[])
    )

    assert "King Alden IV of valenreach" in prompt
    assert "steadfast" in prompt
    assert "prosperity" in prompt


async def test_generate_ruler_backstory_returns_the_clients_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generate = AsyncMock(return_value="Crowned in the autumn mists.")
    monkeypatch.setattr(text_gen_client, "generate_text", generate)

    result = await ruler_backstory_service.generate_ruler_backstory(_request())

    assert result == "Crowned in the autumn mists."
    prompt, max_tokens, timeout = generate.await_args.args
    assert "King Alden IV" in prompt
    assert max_tokens == ruler_backstory_service.BACKSTORY_MAX_OUTPUT_TOKENS
    assert timeout > 0
