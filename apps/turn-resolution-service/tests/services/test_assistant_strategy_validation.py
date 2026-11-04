"""Unit tests for assistant_strategy_validation."""

from app.models.assistant import (
    AssistantStrategyContext,
    AssistantStrategyFaction,
    AssistantStrategyRegion,
)
from app.services.assistant_strategy_validation import find_strategy_validations


def _context() -> AssistantStrategyContext:
    return AssistantStrategyContext(
        factions=[
            AssistantStrategyFaction(
                faction_id="north", name="North", leader_id="north_ruler"
            ),
            AssistantStrategyFaction(
                faction_id="south", name="South", leader_id="south_ruler"
            ),
        ],
        regions=[
            AssistantStrategyRegion(region_id="r1"),
            AssistantStrategyRegion(region_id="r2"),
        ],
    )


def _errors(target: str, content: str) -> list[str]:
    results = find_strategy_validations([(0, target, content)], _context())
    return [str(error) for result in results for error in result["errors"]]  # type: ignore[union-attr]


def test_valid_relation_has_no_errors() -> None:
    body = '{"faction_a": "north", "faction_b": "south", "status": "war"}'
    assert _errors("relation", body) == []


def test_relation_with_unknown_faction_and_bad_status_is_flagged() -> None:
    body = '{"faction_a": "north", "faction_b": "ghost", "status": "feud"}'
    errors = _errors("relation", body)
    assert any("ghost" in error for error in errors)
    assert any("war, peace or alliance" in error for error in errors)


def test_invalid_json_is_flagged() -> None:
    assert _errors("claim", "{nope") == ["Suggestion is not valid JSON."]


def test_temp_id_from_earlier_faction_block_is_known_to_later_blocks() -> None:
    blocks = [
        (0, "faction", '{"temp_id": "east", "name": "East"}'),
        (1, "claim", '{"faction_id": "east", "region_id": "r1"}'),
    ]
    assert find_strategy_validations(blocks, _context()) == []


def test_claim_before_its_faction_block_is_flagged() -> None:
    blocks = [
        (0, "claim", '{"faction_id": "east", "region_id": "r1"}'),
        (1, "faction", '{"temp_id": "east", "name": "East"}'),
    ]
    results = find_strategy_validations(blocks, _context())
    assert [result["index"] for result in results] == [0]


def test_grudge_uses_leader_ids_and_opinion_range() -> None:
    body = '{"holder_id": "north", "target_id": "south_ruler", "opinion": 500}'
    errors = _errors("grudge", body)
    assert any("holder_id" in error for error in errors)
    assert any("opinion" in error for error in errors)


def test_timing_requires_end_year_after_start_year() -> None:
    body = '{"start_year": 1000, "start_month": 13, "end_year": 1000}'
    errors = _errors("timing", body)
    assert any("start_month" in error for error in errors)
    assert any("end_year" in error for error in errors)


def test_rules_reject_unknown_keys_and_out_of_range_percent() -> None:
    errors = _errors("rules", '{"dragons": true, "conditional_gate_percent": 250}')
    assert any("dragons" in error for error in errors)
    assert any("conditional_gate_percent" in error for error in errors)


def test_army_rejects_unknown_troop_type() -> None:
    body = '{"owner_id": "north", "location_id": "r1", "troops": {"dragons": 3}}'
    assert any("troops" in error for error in _errors("army", body))


def test_overlong_title_is_flagged() -> None:
    assert _errors("title", "x" * 300)


def test_unrelated_targets_are_ignored() -> None:
    assert _errors("lore", "anything") == []


def test_new_factions_ruler_can_be_referenced_in_the_same_reply() -> None:
    blocks = [
        (0, "faction", '{"temp_id": "east", "name": "East", "leader_name": "Aria"}'),
        (1, "grudge", '{"holder_id": "east_ruler", "target_id": "north_ruler"}'),
        (
            2,
            "leader_history",
            '{"leader_id": "east_ruler", "history": "Born in exile."}',
        ),
    ]
    assert find_strategy_validations(blocks, _context()) == []


def test_ruler_of_a_faction_never_introduced_is_flagged() -> None:
    body = '{"holder_id": "west_ruler", "target_id": "north_ruler"}'
    assert any("west_ruler" in error for error in _errors("grudge", body))


def test_region_setup_rejects_negative_economy_figures() -> None:
    body = '{"region_id": "r1", "population": -5, "wealth": 10, "garrison": -1}'
    errors = _errors("region_setup", body)
    assert any("population" in error for error in errors)
    assert any("garrison" in error for error in errors)


def test_army_rejects_negative_or_fractional_troop_counts() -> None:
    body = '{"owner_id": "north", "location_id": "r1", "troops": {"infantry": -3, "cavalry": 2.5}}'
    errors = _errors("army", body)
    assert any("troops.infantry" in error for error in errors)
    assert any("troops.cavalry" in error for error in errors)


def test_faction_rejects_out_of_range_stability_and_negative_treasury() -> None:
    body = '{"temp_id": "east", "name": "East", "stability": 140, "treasury": -1}'
    errors = _errors("faction", body)
    assert any("stability" in error for error in errors)
    assert any("treasury" in error for error in errors)


def test_timing_rejects_a_lone_negative_year() -> None:
    assert any(
        "start_year" in error for error in _errors("timing", '{"start_year": -4}')
    )


def test_new_rules_accept_letters_and_judgments_and_refuse_bad_values() -> None:
    good = '{"letters_enabled": true, "judgment_sentence_turns": 3}'
    assert _errors("rules", good) == []
    bad = '{"letters_enabled": "yes", "letter_cooldown_turns": 0}'
    errors = _errors("rules", bad)
    assert any("letters_enabled" in error for error in errors)
    assert any("letter_cooldown_turns" in error for error in errors)
