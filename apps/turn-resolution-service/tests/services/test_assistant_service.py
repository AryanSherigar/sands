"""Unit tests for assistant_service."""

from app.models.assistant import (
    AssistantChatMessage,
    AssistantChatRequest,
    AssistantDraftContext,
    AssistantEntitySummary,
    AssistantMasterContext,
    AssistantScopedContext,
    AssistantStoryCard,
    AssistantStrategyContext,
    AssistantStrategyFaction,
    AssistantStrategyRegion,
    AssistantStrategyRelation,
    AssistantStrategyTiming,
)
from app.services.assistant_service import (
    build_system_instruction,
    format_chat_contents,
)


def test_build_system_instruction_without_draft() -> None:
    request = AssistantChatRequest(messages=[])
    instruction = build_system_instruction(request)
    assert "You are an immersive world-building co-author" in instruction
    assert "ACTION BLOCKS:" in instruction


def test_build_system_instruction_with_draft() -> None:
    draft = AssistantDraftContext(
        title="Chronicles of Elyria",
        genre_tags=["Dark Fantasy", "Gothic"],
        world_lore="Ancient dragons ruled the sky.",
        story_cards=[
            AssistantStoryCard(
                type="Faction", name="Silver Dawn", content="Holy knights"
            )
        ],
        active_section="lore",
    )
    request = AssistantChatRequest(messages=[], draft_context=draft)
    instruction = build_system_instruction(request)
    assert "Chronicles of Elyria" in instruction
    assert "Dark Fantasy, Gothic" in instruction
    assert "Silver Dawn" in instruction
    assert "Active Wizard Section: lore" in instruction


def test_build_system_instruction_master_mode_with_context() -> None:
    context = AssistantMasterContext(
        title="Sunken Kingdom",
        active_tab="entities",
        entities=[
            AssistantEntitySummary(
                entity_id="entity-1",
                entity_type="character",
                canonical_name="Hero",
            )
        ],
    )
    request = AssistantChatRequest(messages=[], mode="master", master_context=context)
    instruction = build_system_instruction(request)
    assert "game systems designer" in instruction
    assert "Sunken Kingdom" in instruction
    assert "Hero" in instruction
    assert "action:entity" in instruction
    assert "world-building co-author" not in instruction


def test_build_system_instruction_master_mode_without_context() -> None:
    request = AssistantChatRequest(messages=[], mode="master")
    instruction = build_system_instruction(request)
    assert "game systems designer" in instruction
    assert "action:fact" in instruction


def test_format_chat_contents() -> None:
    messages = [
        AssistantChatMessage(role="user", content="Hi!"),
        AssistantChatMessage(role="assistant", content="Greetings creator."),
    ]
    contents = format_chat_contents(messages)
    assert len(contents) == 2
    assert contents[0].role == "user"
    assert contents[0].parts[0].text == "Hi!"
    assert contents[1].role == "model"
    assert contents[1].parts[0].text == "Greetings creator."


def test_master_prompt_teaches_the_mutation_list_one_shot_and_hidden_fields() -> None:
    from app.services import assistant_service

    guide = assistant_service._MASTER_ACTION_SYNTAX_GUIDE

    assert '"state_mutations": [' in guide
    assert '"state_mutation": {' not in guide
    assert '"is_one_shot": false' in guide
    assert "sensory_cue" in guide
    assert '"hidden": false}' in guide


def _scoped_request(tab_text: str = "The lamp must stay lit.") -> AssistantChatRequest:
    return AssistantChatRequest(
        messages=[],
        mode="scoped",
        scoped_context=AssistantScopedContext(
            one_line_idea="A keeper guards a failing light.",
            tab_kind="always_remember",
            tab_label="Always remember",
            tab_text=tab_text,
        ),
    )


def test_scoped_instruction_carries_the_idea_and_only_the_active_tab() -> None:
    instruction = build_system_instruction(_scoped_request())

    assert "world-building co-author" in instruction
    assert "ACTION BLOCKS:" in instruction
    assert "CURRENT TAB IN STUDIO:" in instruction
    assert "A keeper guards a failing light." in instruction
    assert "Always remember" in instruction
    assert "The lamp must stay lit." in instruction
    assert "CURRENT SCENARIO DRAFT IN STUDIO:" not in instruction
    assert "CURRENT MASTER-MODE SCENARIO DATA:" not in instruction


def test_scoped_instruction_with_empty_tab_text_still_sends_the_idea() -> None:
    instruction = build_system_instruction(_scoped_request(tab_text=""))

    assert "A keeper guards a failing light." in instruction
    assert "(Empty)" in instruction


def test_scoped_instruction_without_context_is_persona_and_guide_only() -> None:
    instruction = build_system_instruction(
        AssistantChatRequest(messages=[], mode="scoped")
    )

    assert "ACTION BLOCKS:" in instruction
    assert "CURRENT TAB IN STUDIO:" not in instruction


def test_old_contexts_are_still_ignored_in_scoped_mode_and_vice_versa() -> None:
    request = _scoped_request().model_copy(
        update={"draft_context": AssistantDraftContext(title="Old Draft")}
    )

    assert "Old Draft" not in build_system_instruction(request)


def _strategy_context() -> AssistantStrategyContext:
    return AssistantStrategyContext(
        title="Two Crowns",
        timing=AssistantStrategyTiming(start_year=1000, start_month=3, end_year=1004),
        factions=[
            AssistantStrategyFaction(
                faction_id="south", name="South", leader_id="south_ruler"
            ),
            AssistantStrategyFaction(
                faction_id="north", name="North", leader_id="north_ruler"
            ),
        ],
        regions=[AssistantStrategyRegion(region_id="r1", name="Ironvale")],
        relations=[
            AssistantStrategyRelation(
                faction_a="north", faction_b="south", status="war"
            )
        ],
    )


def test_strategy_instruction_carries_persona_guide_and_sorted_context() -> None:
    instruction = build_system_instruction(
        AssistantChatRequest(
            messages=[], mode="strategy", strategy_context=_strategy_context()
        )
    )

    assert "grand-strategy scenario designer" in instruction
    assert "action:relation" in instruction
    assert "CURRENT STRATEGY SCENARIO DATA:" in instruction
    assert "Ironvale" in instruction
    assert instruction.index("- north:") < instruction.index("- south:")
    assert "CURRENT SCENARIO DRAFT IN STUDIO:" not in instruction


def test_strategy_instruction_without_context_is_persona_and_guide_only() -> None:
    instruction = build_system_instruction(
        AssistantChatRequest(messages=[], mode="strategy")
    )

    assert "ACTION BLOCKS:" in instruction
    assert "CURRENT STRATEGY SCENARIO DATA:" not in instruction
