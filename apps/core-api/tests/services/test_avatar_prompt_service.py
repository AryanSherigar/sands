import pytest
from app.services.avatar_prompt_service import (
    FRAMING_DIRECTIVE,
    build_avatar_optimization_instruction,
    optimize_avatar_prompt,
)


def test_build_avatar_optimization_instruction_contains_rigging_rules():
    instruction = build_avatar_optimization_instruction(
        "Proud elven queen in silver battle armor"
    )
    assert "front-facing" in instruction.lower()
    assert "closed mouth" in instruction.lower()
    assert "shoulders" in instruction.lower()
    assert "neutral background" in instruction.lower()


@pytest.mark.asyncio
async def test_optimize_avatar_prompt_fallback_when_empty():
    res = await optimize_avatar_prompt("")
    assert "portrait" in res.lower()


@pytest.mark.asyncio
async def test_optimize_avatar_prompt_with_description():
    res = await optimize_avatar_prompt("Stern Viking chieftain with braided beard")
    assert "front-facing" in res.lower()
    assert "viking chieftain" in res.lower()
    assert "closed mouth" in res.lower()


@pytest.mark.asyncio
async def test_optimize_avatar_prompt_pins_face_framing_for_the_rig():
    res = await optimize_avatar_prompt("Stern Viking chieftain")
    assert FRAMING_DIRECTIVE in res
    assert FRAMING_DIRECTIVE in build_avatar_optimization_instruction("anything")
