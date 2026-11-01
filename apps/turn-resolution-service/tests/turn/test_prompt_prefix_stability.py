"""The narration and Studio prompts keep a byte-stable head between turns.

Each test renders two consecutive turns of fixed inputs
(`prompt_fixtures.py`) and asserts where they may differ (ADR-21).
"""

import copy
import uuid

from app.models.turn import LoadedState
from app.services.assistant_service import build_system_instruction
from app.turn import context_assembly, tool_definitions
from app.turn.steps import ai_orchestrator
from prefix_stability import assert_shared_through
from prompt_fixtures import (
    ALWAYS_REMEMBER,
    NARRATOR_INSTRUCTION,
    SCENARIO_PREMISE,
    NarrationInputs,
    assistant_requests,
    newbie_turns,
    night_desk_turns,
)

STATE_BOUNDARY = "## Current State"
MEMORY_BOUNDARY = "## Story Memory"
DIRECTIVES_HEADING = "## Narrator Directives"
FACTS_HEADING = "## Established Facts"
SCENARIO_HEADING = "## Scenario"
PLAYER_HEADING = "## Player Character"
MEMORY_CLOSE = "</memory>"
PLAYER_DIRECTIVE_MARKER = "Address the player character"
DRAFT_BOUNDARY = "CURRENT SCENARIO DRAFT IN STUDIO:"
MASTER_BOUNDARY = "CURRENT MASTER-MODE SCENARIO DATA:"
SCOPED_BOUNDARY = "CURRENT TAB IN STUDIO:"


def _master_system(inputs: NarrationInputs) -> str:
    return ai_orchestrator._build_master_system_instruction(inputs.loaded_state)


def _prompt(inputs: NarrationInputs, master: bool) -> str:
    directives = (
        ai_orchestrator._collect_directives(
            inputs.loaded_state, inputs.active_instructions
        )
        if master
        else ()
    )
    return context_assembly.assemble_prompt(
        inputs.request, inputs.loaded_state, inputs.context, directives
    )


def test_master_system_instruction_is_identical_between_turns() -> None:
    first, second = night_desk_turns()

    assert _master_system(first) == _master_system(second)


def test_master_prompt_head_is_identical_through_the_state_block() -> None:
    first, second = night_desk_turns()

    assert_shared_through(
        _prompt(first, master=True), _prompt(second, master=True), STATE_BOUNDARY
    )


def test_field_descriptions_sit_in_the_state_block_and_keep_the_head_stable() -> None:
    first, second = night_desk_turns()
    for turn in (first, second):
        schema = turn.loaded_state.scenario_snapshot["state_schema"]
        schema["sanity"]["description"] = "Falls as the night gets stranger"

    first_prompt = _prompt(first, master=True)
    second_prompt = _prompt(second, master=True)

    assert_shared_through(first_prompt, second_prompt, STATE_BOUNDARY)
    assert "(Falls as the night gets stranger)" in first_prompt.split(STATE_BOUNDARY)[1]
    assert (
        "(Falls as the night gets stranger)"
        not in first_prompt.split(STATE_BOUNDARY)[0]
    )
    assert _master_system(first) == _master_system(second)


def test_master_tools_are_identical_between_turns() -> None:
    first, second = night_desk_turns()

    first_tools = tool_definitions.build_master_mode_tools(
        first.loaded_state.scenario_snapshot
    )
    second_tools = tool_definitions.build_master_mode_tools(
        second.loaded_state.scenario_snapshot
    )

    assert first_tools.model_dump_json() == second_tools.model_dump_json()


def test_per_turn_directives_live_only_in_the_late_directives_block() -> None:
    _first, second = night_desk_turns()
    system = _master_system(second)
    prompt = _prompt(second, master=True)

    directives = prompt[prompt.index(DIRECTIVES_HEADING) :]
    assert "The lamp flickers" in directives
    assert NARRATOR_INSTRUCTION in directives
    assert "Known paths from here" in directives
    assert "The lamp flickers" not in system
    assert NARRATOR_INSTRUCTION not in system
    assert "Known paths from here" not in system
    assert prompt.index(DIRECTIVES_HEADING) > prompt.index(STATE_BOUNDARY)


def test_facts_block_sits_in_the_tail_outside_memory_and_system_instruction() -> None:
    _first, second = night_desk_turns()
    system = _master_system(second)
    prompt = _prompt(second, master=True)

    assert FACTS_HEADING in prompt
    assert FACTS_HEADING not in system
    assert prompt.index(FACTS_HEADING) > prompt.index(STATE_BOUNDARY)
    assert prompt.index(FACTS_HEADING) > prompt.index(MEMORY_CLOSE)
    assert prompt.index(FACTS_HEADING) < prompt.index(DIRECTIVES_HEADING)


def test_facts_block_carries_location_clock_and_never_describe_items() -> None:
    first, second = night_desk_turns()

    first_facts = _prompt(first, master=True).split(FACTS_HEADING)[1]
    second_facts = _prompt(second, master=True).split(FACTS_HEADING)[1]

    assert "Location:" in first_facts and "Clock: 11:00 PM" in first_facts
    assert "Never describe the inside of Cabin 14" in first_facts
    assert "Cabin 14 lamp: on" in first_facts
    assert (
        first_facts.split(DIRECTIVES_HEADING)[0]
        != second_facts.split(DIRECTIVES_HEADING)[0]
    )


def test_turn_without_directives_has_no_directives_block() -> None:
    first, _second = night_desk_turns()
    prompt = context_assembly.assemble_prompt(
        first.request, first.loaded_state, first.context
    )

    assert DIRECTIVES_HEADING not in prompt


def test_newbie_system_instruction_and_prompt_head_are_identical_between_turns() -> (
    None
):
    first, second = newbie_turns()

    assert ai_orchestrator._build_system_instruction(
        first.loaded_state
    ) == ai_orchestrator._build_system_instruction(second.loaded_state)
    assert_shared_through(
        _prompt(first, master=False), _prompt(second, master=False), MEMORY_BOUNDARY
    )


def test_players_of_one_scenario_share_the_system_instruction_up_to_their_name() -> (
    None
):
    first, _second = night_desk_turns()
    kaelen = _with_player(first.loaded_state, "Kaelen")
    mara = _with_player(first.loaded_state, "Mara")

    system_kaelen = ai_orchestrator._build_master_system_instruction(kaelen)
    system_mara = ai_orchestrator._build_master_system_instruction(mara)

    assert system_kaelen != system_mara
    assert_shared_through(system_kaelen, system_mara, PLAYER_DIRECTIVE_MARKER)


def _with_player(loaded_state: LoadedState, name: str) -> LoadedState:
    snapshot = copy.deepcopy(loaded_state.scenario_snapshot)
    snapshot["entities"].append(
        {
            "entity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "player")),
            "canonical_name": "The Clerk",
            "is_player": True,
        }
    )
    state = {**loaded_state.state, "setup": {"character_name": name}}
    return loaded_state.model_copy(
        update={"scenario_snapshot": snapshot, "state": state}
    )


def test_persona_sits_before_the_playthrough_specific_directive() -> None:
    first, _second = night_desk_turns()
    system = ai_orchestrator._build_master_system_instruction(
        _with_player(first.loaded_state, "Kaelen")
    )

    persona = str(first.loaded_state.scenario_snapshot["narrator_persona"])
    assert system.index(persona.strip()[:40]) < system.index(PLAYER_DIRECTIVE_MARKER)


def test_assistant_head_is_identical_when_the_draft_changes() -> None:
    requests = assistant_requests()
    first_newbie, second_newbie = requests["newbie"]
    first_master, second_master = requests["master"]

    assert_shared_through(
        build_system_instruction(first_newbie),
        build_system_instruction(second_newbie),
        DRAFT_BOUNDARY,
    )
    assert_shared_through(
        build_system_instruction(first_master),
        build_system_instruction(second_master),
        MASTER_BOUNDARY,
    )


def test_assistant_persona_and_guide_come_before_the_context() -> None:
    first_newbie, _ = assistant_requests()["newbie"]
    instruction = build_system_instruction(first_newbie)

    assert instruction.index("ACTION BLOCKS:") < instruction.index(DRAFT_BOUNDARY)


ALREADY_DESCRIBED_HEADING = "## Already Described"


def test_already_described_sits_in_the_tail_and_never_in_the_system_instruction() -> (
    None
):
    _first, second = night_desk_turns()
    system = _master_system(second)
    prompt = _prompt(second, master=True)

    assert ALREADY_DESCRIBED_HEADING in prompt
    assert ALREADY_DESCRIBED_HEADING not in system
    assert prompt.index(ALREADY_DESCRIBED_HEADING) > prompt.index(MEMORY_CLOSE)
    assert prompt.index(ALREADY_DESCRIBED_HEADING) > prompt.index(FACTS_HEADING)
    assert prompt.index(ALREADY_DESCRIBED_HEADING) < prompt.index(DIRECTIVES_HEADING)


def _scenario_block(prompt: str) -> str:
    start = prompt.index(SCENARIO_HEADING)
    return prompt[start : prompt.index("\n\n", start)]


def test_newbie_scenario_block_is_in_the_shared_head_and_identical_between_turns() -> (
    None
):
    first, second = newbie_turns()
    first_prompt = _prompt(first, master=False)
    second_prompt = _prompt(second, master=False)

    assert_shared_through(first_prompt, second_prompt, MEMORY_BOUNDARY)
    assert first_prompt.index(SCENARIO_HEADING) < first_prompt.index(MEMORY_BOUNDARY)
    block = _scenario_block(first_prompt)
    assert block == _scenario_block(second_prompt)
    assert SCENARIO_PREMISE in block
    assert "- Mood: eerie, tense" in block
    assert all(f"  - {line}" in block for line in ALWAYS_REMEMBER)


def test_master_scenario_block_is_in_the_shared_head_and_identical_between_turns() -> (
    None
):
    first, second = night_desk_turns()
    first_prompt = _prompt(first, master=True)
    second_prompt = _prompt(second, master=True)

    assert_shared_through(first_prompt, second_prompt, STATE_BOUNDARY)
    assert first_prompt.index(SCENARIO_HEADING) < first_prompt.index(STATE_BOUNDARY)
    block = _scenario_block(first_prompt)
    assert block == _scenario_block(second_prompt)
    assert all(f"  - {line}" in block for line in ALWAYS_REMEMBER)


def test_scenario_block_leads_the_prompt_ahead_of_the_player_and_per_turn_blocks() -> (
    None
):
    first, _second = newbie_turns()
    prompt = _prompt(first, master=False)

    assert prompt.startswith(SCENARIO_HEADING)
    assert prompt.index(SCENARIO_HEADING) < prompt.index(PLAYER_HEADING)


def test_scoped_assistant_head_is_identical_when_the_tab_changes() -> None:
    first, second = assistant_requests()["scoped"]
    first_instruction = build_system_instruction(first)
    second_instruction = build_system_instruction(second)

    assert_shared_through(first_instruction, second_instruction, SCOPED_BOUNDARY)
    assert first_instruction != second_instruction
    assert first_instruction.index("ACTION BLOCKS:") < first_instruction.index(
        SCOPED_BOUNDARY
    )


def test_scoped_assistant_keeps_the_idea_right_after_the_boundary() -> None:
    first, second = assistant_requests()["scoped"]

    for request in (first, second):
        tail = build_system_instruction(request).split(SCOPED_BOUNDARY)[1]
        assert tail.lstrip().startswith("One line idea: A keeper guards")
