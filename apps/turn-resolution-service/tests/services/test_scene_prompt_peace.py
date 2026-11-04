from app.services import scene_prompt, scene_prompt_peace
from app.services.scene_prompt_treaty import verdict_hint
from strategy_contracts.scene import (
    SceneType,
    WarStanding,
)
from strategy_contracts.scene_exchange import SceneExchangeView
from strategy_contracts.treaty import Verdict
from tests.services.peace_fixtures import peace_package as _package
from tests.turn.prefix_stability import assert_shared_through


def _exchange(sequence: int, player: str, leader: str) -> SceneExchangeView:
    return SceneExchangeView(sequence=sequence, player_text=player, leader_text=leader)


def _render(system: str, contents) -> str:
    parts = [system] + [
        f"{item.role}: {part.text}" for item in contents for part in item.parts
    ]
    return "\n".join(parts)


def test_a_peace_scene_has_a_prompt_profile() -> None:
    system = scene_prompt.build_system_instruction(_package())

    assert "peace" in system.lower()
    assert "Mira of Ashford" in system


def test_the_brief_names_both_factions_with_ids_and_the_regions_at_stake() -> None:
    brief = scene_prompt.build_system_instruction(_package()).split("PRIVATE BRIEF")[1]

    assert "Ashford (id house_ashford)" in brief
    assert "Carrow (id house_carrow)" in brief
    assert "Elmstead (id elmstead)" in brief
    assert "Brennmoor (id brennmoor)" in brief


def test_the_brief_lists_tiers_and_which_need_a_guarantor() -> None:
    brief = scene_prompt.build_system_instruction(_package()).split("PRIVATE BRIEF")[1]

    assert "short: 6 turns" in brief
    assert "generation: 60 turns, needs a guarantor" in brief
    assert "perpetual: never ends, needs a guarantor" in brief


def test_the_leaders_stance_follows_the_war_standing() -> None:
    leading = scene_prompt.build_system_instruction(_package(WarStanding.LEADING))
    trailing = scene_prompt.build_system_instruction(_package(WarStanding.TRAILING))

    assert "winning" in leading.split("PRIVATE BRIEF")[1]
    assert "losing" in trailing.split("PRIVATE BRIEF")[1]


def test_grudges_are_spoken_at_the_peace_table_too() -> None:
    brief = scene_prompt.build_system_instruction(_package()).split("PRIVATE BRIEF")[1]

    assert "[g1] (firm) You raided our granaries." in brief


def test_no_hidden_threshold_appears_in_the_prompt() -> None:
    system = scene_prompt.build_system_instruction(_package())

    assert "37" not in system
    assert "accept_at" not in system


def test_the_private_brief_stays_out_of_user_and_model_turns() -> None:
    transcript = [_exchange(1, "Peace?", "Perhaps.")]
    contents = scene_prompt.build_reply_contents(
        transcript, "A truce?", 6, SceneType.PEACE
    )
    contents += scene_prompt.build_decision_contents(
        transcript, "A truce?", "We shall see.", 6, SceneType.PEACE
    )
    text = " ".join(part.text for item in contents for part in item.parts)

    assert "PRIVATE BRIEF" not in text
    assert "granaries" not in text
    assert "house_ashford" not in text


def test_two_consecutive_peace_exchanges_share_the_system_and_first_quote() -> None:
    system = scene_prompt.build_system_instruction(_package())
    first = scene_prompt.build_reply_contents([], "Let us talk.", 6, SceneType.PEACE)
    second = scene_prompt.build_reply_contents(
        [_exchange(1, "Let us talk.", "Go on.")], "A truce?", 6, SceneType.PEACE
    )

    assert_shared_through(
        _render(system, first), _render(system, second), "</player_says>"
    )


def test_the_decision_directive_describes_the_peace_json() -> None:
    directive = scene_prompt.profile_for(SceneType.PEACE).decision_directive

    for key in (
        "peace_tier",
        "guarantor_ids",
        "pay_gold",
        "cede_region",
        "cited_grudge_ids",
    ):
        assert key in directive


def test_the_system_instruction_is_deterministic() -> None:
    package = _package()

    assert scene_prompt.build_system_instruction(
        package
    ) == scene_prompt.build_system_instruction(package.model_copy(deep=True))


def test_the_peace_directive_keeps_the_marker_the_harness_keys_on() -> None:
    directive = scene_prompt.profile_for(SceneType.PEACE).decision_directive

    assert "Answer with only a JSON" in directive


def test_rules_stop_a_goal_from_being_read_as_a_holding() -> None:
    assert "not something the player holds" in scene_prompt_peace.PEACE_RULES


def test_a_refused_peace_offer_is_hinted_in_the_final_turn_only() -> None:
    package = _package()
    profile = scene_prompt.profile_for_package(package)
    refused = SceneExchangeView(
        sequence=1, player_text="Peace.", leader_text="Terms?", verdict=Verdict.REFUSE
    )

    contents = scene_prompt.build_reply_contents(
        [refused], "Again.", 6, profile=profile
    )

    hint = verdict_hint(Verdict.REFUSE)
    assert hint is not None and hint in contents[-1].parts[0].text
    assert all(hint not in part.text for item in contents[:-1] for part in item.parts)
    assert hint not in scene_prompt.build_system_instruction(package)


def test_rules_stop_the_ruler_inventing_troop_movements() -> None:
    assert "Never state where armies are" in scene_prompt_peace.PEACE_RULES
