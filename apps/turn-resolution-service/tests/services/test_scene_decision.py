import pytest
from app.services.scene_decision import parse_decision
from strategy_contracts.scene_exchange import SceneAction
from strategy_contracts.terms import PromiseKind


def test_a_clean_json_answer_is_read() -> None:
    decision = parse_decision('{"action": "propose_terms", "duration_turns": 8}')
    assert (decision.action, decision.duration_turns) == (SceneAction.PROPOSE_TERMS, 8)


def test_json_wrapped_in_prose_or_fences_is_still_read() -> None:
    text = 'Sure.\n```json\n{"action": "walk_out", "duration_turns": null}\n```'
    assert parse_decision(text).action is SceneAction.WALK_OUT


@pytest.mark.parametrize(
    "text",
    [
        "",
        "I think they agreed.",
        '{"action": "shrug"}',
        '{"action": "propose_terms", "duration_turns": 0}',
        '{"action": "refuse", "extra": true}',
        "{not json}",
    ],
)
def test_anything_unusable_means_keep_talking(text) -> None:
    decision = parse_decision(text)
    assert (decision.action, decision.duration_turns) == (
        SceneAction.CONTINUE_TALK,
        None,
    )


def test_cited_grudge_ids_are_read() -> None:
    decision = parse_decision(
        '{"action": "continue_talk", "cited_grudge_ids": ["g1", "g2"]}'
    )
    assert decision.cited_grudge_ids == ["g1", "g2"]


def test_too_many_cited_ids_are_trimmed_not_fatal() -> None:
    decision = parse_decision(
        '{"action": "walk_out", "cited_grudge_ids": ["g1", "g2", "g3", "g4", "g5"]}'
    )
    assert decision.action is SceneAction.WALK_OUT
    assert decision.cited_grudge_ids == ["g1", "g2", "g3"]


PEACE_JSON = (
    '{"action": "propose_terms", "peace_tier": "medium", "is_white_peace": false, '
    '"guarantor_ids": ["house_dunwick"], "terms": ['
    '{"kind": "pay_gold", "payer_id": "house_a", "payee_id": "house_b", "amount": 40}, '
    '{"kind": "cede_region", "from_faction_id": "house_a", "to_faction_id": "house_b", '
    '"region_id": "elmstead"}], "cited_grudge_ids": ["g1"]}'
)


def test_a_peace_decision_with_nested_terms_is_read_whole() -> None:
    decision = parse_decision(f"Here you go:\n```json\n{PEACE_JSON}\n```")

    assert decision.action is SceneAction.PROPOSE_TERMS
    assert decision.peace_tier == "medium"
    assert [term.kind for term in decision.terms] == ["pay_gold", "cede_region"]
    assert decision.guarantor_ids == ["house_dunwick"]
    assert decision.cited_grudge_ids == ["g1"]


def test_a_malformed_term_is_dropped_but_the_decision_survives() -> None:
    text = (
        '{"action": "propose_terms", "peace_tier": "short", "terms": ['
        '{"kind": "pay_gold", "payer_id": "house_a"}, '
        '{"kind": "cede_region", "from_faction_id": "house_a", "to_faction_id": "house_b", '
        '"region_id": "elmstead"}]}'
    )

    decision = parse_decision(text)

    assert decision.action is SceneAction.PROPOSE_TERMS
    assert [term.kind for term in decision.terms] == ["cede_region"]


def test_an_unknown_peace_tier_keeps_the_action_without_a_tier() -> None:
    decision = parse_decision('{"action": "propose_terms", "peace_tier": "forever"}')

    assert decision.action is SceneAction.PROPOSE_TERMS
    assert decision.peace_tier is None


def test_a_flat_promise_answer_is_read() -> None:
    text = (
        'The ruler swore. {"action": "propose_terms", "duration_turns": 8, '
        '"promise_kind": "never_attack_faction", "promise_subject_id": null, '
        '"is_promise_by_ruler": true}'
    )
    decision = parse_decision(text)
    assert decision.action is SceneAction.PROPOSE_TERMS
    assert decision.promise_kind is PromiseKind.NEVER_ATTACK_FACTION
    assert decision.is_promise_by_ruler is True


def test_a_promise_with_a_subject_is_read() -> None:
    text = (
        '{"action": "propose_terms", "duration_turns": 5, '
        '"promise_kind": "never_ally_with", "promise_subject_id": "house_dunwick"}'
    )
    decision = parse_decision(text)
    assert decision.promise_subject_id == "house_dunwick"
    assert decision.is_promise_by_ruler is False


def test_an_unknown_promise_kind_means_keep_talking() -> None:
    text = '{"action": "propose_terms", "duration_turns": 5, "promise_kind": "gift"}'
    decision = parse_decision(text)
    assert (decision.action, decision.promise_kind) == (
        SceneAction.CONTINUE_TALK,
        None,
    )
