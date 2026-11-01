from dataclasses import replace

from eval import baseline_text
from eval.baseline_text import build_inline_text, estimate_tokens
from eval.corpus_models import EntityDef, ProbeDef, SnapshotDef
from eval.keys import key_uuid
from eval.payloads import (
    build_register_items,
    build_retrieve_request,
    build_template_request,
    build_turn_items,
    render_recent_text,
)
from tests.evaluation.campaign_helpers import make_campaign, make_turn


def _probe(at_turn: int = 3, action_text: str = "I ask the warden.") -> ProbeDef:
    return ProbeDef(
        probe_id="p",
        failure_class="long_range",
        at_turn=at_turn,
        action_text=action_text,
        action_mode="say",
        actor_key="p1",
        required=["pl_oath"],
        expected_truth="x",
    )


def _newbie(paragraph_count: int, paragraph_words: int = 200):
    campaign = make_campaign()
    lore = "\n\n".join(
        f"P{i} " + "word " * paragraph_words for i in range(paragraph_count)
    )
    scenario = campaign.scenario.model_copy(
        update={
            "mode": "newbie",
            "world_lore": lore,
            "main_conflict": "A war.",
            "opening_prompt": "It begins.",
        }
    )
    return replace(campaign, scenario=scenario)


def test_master_template_request_uses_stable_ids() -> None:
    campaign = make_campaign()
    request = build_template_request(campaign)
    assert (
        request.mode == "master"
        and request.newbie is None
        and request.master is not None
    )
    assert request.master.entities[0].entity_id == key_uuid("T1", "mira")
    assert request.master.facts[0].fact_id == key_uuid("T1", "vale_rank")
    assert build_template_request(campaign) == request


def test_newbie_template_request_carries_lore_and_cards() -> None:
    request = build_template_request(_newbie(2))
    assert request.master is None and request.newbie is not None
    assert request.newbie.story_cards[0].card_id == "c1"
    assert "P0" in request.newbie.world_lore


def test_register_item_names_participants_and_player_entity() -> None:
    item = build_register_items(make_campaign(), "playthrough")[0]
    assert item.payload.player_entity is not None
    assert item.payload.participants[0].display_name == "Mira"


def test_turn_items_are_deterministic_and_match_sequence() -> None:
    campaign = make_campaign()
    first = build_turn_items(campaign, campaign.turns, "playthrough")
    second = build_turn_items(campaign, campaign.turns, "playthrough")
    assert first == second
    assert [item.sequence for item in first] == list(range(1, 9))
    assert first[1].payload.rejected_calls[0].tool_name == "x"


def test_delta_key_is_entity_uuid_dot_attribute() -> None:
    campaign = make_campaign()
    delta = {
        "kind": "state_mutation",
        "entity_key": "vale",
        "attribute": "hp",
        "before": 9,
        "after": 7,
    }
    turn = make_turn(1, "x", delta=[delta])
    item = build_turn_items(campaign, [turn], "playthrough")[0]
    assert item.payload.accepted_delta.items[0].key == f"{key_uuid('T1', 'vale')}.hp"


def test_retrieve_request_follows_snapshot_and_sequence() -> None:
    campaign = make_campaign()
    snapshot = SnapshotDef(scene_entity_keys=["vale"], revealed_fact_keys=["vale_rank"])
    turns = [
        *campaign.turns[:2],
        campaign.turns[2].model_copy(update={"snapshot": snapshot}),
    ]
    request = build_retrieve_request(replace(campaign, turns=turns), _probe())
    assert request.sequence == 3
    assert request.scene_authored_entity_ids == [key_uuid("T1", "vale")]
    assert request.revealed_fact_ids == [key_uuid("T1", "vale_rank")]
    assert len(request.participant_names) == 1


def test_recent_text_covers_only_the_window() -> None:
    turns = [make_turn(number, f"narration {number}") for number in range(1, 10)]
    text = render_recent_text(turns, 9)
    assert "narration 9" in text and "narration 4" in text and "narration 3" not in text


def test_baseline_constants_match_the_documented_values() -> None:
    assert baseline_text.LORE_FALLBACK_TOKENS == 1500
    assert baseline_text.CHARS_PER_TOKEN == 3
    assert baseline_text.RECENT_WINDOW_TURNS == 6


def test_lore_fallback_keeps_whole_paragraphs_up_to_budget() -> None:
    inline = build_inline_text(_newbie(10), _probe())
    used = sum(chunk.token_count for chunk in inline.lore_chunks)
    assert 0 < len(inline.lore_chunks) < 10 and used <= 1500


def test_master_mode_has_no_lore_fallback() -> None:
    assert build_inline_text(make_campaign(), _probe()).lore_chunks == []


def test_opening_prompt_is_inline_only_while_the_story_is_young() -> None:
    campaign = _newbie(1)
    turns = [make_turn(number, f"n{number}") for number in range(1, 9)]
    campaign = replace(campaign, turns=turns)
    assert "It begins." in build_inline_text(campaign, _probe(at_turn=3)).window_text
    assert (
        "It begins." not in build_inline_text(campaign, _probe(at_turn=8)).window_text
    )
    assert (
        "Main conflict: A war."
        in build_inline_text(campaign, _probe(at_turn=8)).window_text
    )


def test_master_scene_cards_inline_described_non_player_entities() -> None:
    campaign = make_campaign()
    warden = EntityDef(
        key="warden",
        entity_type="character",
        canonical_name="The Warden",
        description="Speaks rarely.",
    )
    scenario = campaign.scenario.model_copy(
        update={"entities": [*campaign.scenario.entities, warden]}
    )
    snapshot = SnapshotDef(scene_entity_keys=["warden", "mira"])
    turns = [
        *campaign.turns[:2],
        campaign.turns[2].model_copy(update={"snapshot": snapshot}),
    ]
    inline = build_inline_text(
        replace(campaign, scenario=scenario, turns=turns), _probe()
    )
    assert "Speaks rarely." in inline.window_text


def test_estimate_tokens_uses_three_chars_per_token() -> None:
    assert estimate_tokens("a" * 9) == 3 and estimate_tokens("a" * 10) == 4


def test_last_say_utterance_is_the_latest_say_turn_in_the_window() -> None:
    from eval.payloads import last_say_utterance

    turns = [
        make_turn(1, "n1", action_text="old words", action_mode="say"),
        make_turn(2, "n2", action_text="I ask about the key.", action_mode="say"),
        make_turn(3, "n3", action_text="I walk away.", action_mode="do"),
    ]
    assert last_say_utterance(turns, 3) == "I ask about the key."
    assert last_say_utterance([make_turn(1, "n1")], 1) == ""


def test_retrieve_request_carries_the_last_say_utterance() -> None:
    campaign = make_campaign()
    turns = [
        campaign.turns[0].model_copy(
            update={"action_mode": "say", "action_text": "Tell me about the ferry."}
        ),
        *campaign.turns[1:],
    ]
    request = build_retrieve_request(replace(campaign, turns=turns), _probe(at_turn=3))
    assert request.last_actor_utterance == "Tell me about the ferry."


def test_newbie_campaign_registers_a_player_entity_named_after_the_owner() -> None:
    from eval.payloads import registered_player_key

    campaign = _newbie(1)
    scenario = campaign.scenario.model_copy(update={"player_entity_key": None})
    campaign = replace(campaign, scenario=scenario)
    item = build_register_items(campaign, "playthrough")[0]
    assert registered_player_key(campaign) == "mira"
    assert item.payload.player_entity is not None
    assert item.payload.player_entity.authored_entity_id == key_uuid("T1", "mira")


def test_newbie_campaign_without_a_matching_entity_gets_a_synthesised_player() -> None:
    from eval.payloads import registered_player_key

    campaign = _newbie(1)
    scenario = campaign.scenario.model_copy(
        update={"player_entity_key": None, "entities": [], "facts": []}
    )
    campaign = replace(campaign, scenario=scenario)
    item = build_register_items(campaign, "playthrough")[0]
    assert registered_player_key(campaign) == "player"
    assert item.payload.player_entity is not None
    assert item.payload.player_entity.canonical_name == "Mira"
    assert item.payload.player_entity.authored_entity_id == key_uuid("T1", "player")


def test_authored_keys_for_newbie_are_only_the_registered_player() -> None:
    from eval.runner import authored_entity_keys

    campaign = _newbie(1)
    campaign = replace(
        campaign,
        scenario=campaign.scenario.model_copy(update={"player_entity_key": None}),
    )
    assert authored_entity_keys(campaign) == {"mira"}
