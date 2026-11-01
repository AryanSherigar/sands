from uuid import UUID

import pytest
from app.models.world_diplomacy import (
    CommitmentState,
    DiplomaticPlayState,
    EnvoyState,
    GroundState,
    OathbreakerMark,
    OutrageState,
    PrisonerKind,
    PrisonerState,
    RelationState,
    TruceState,
    WarState,
)
from pydantic import ValidationError
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.enums import RelationStatus
from strategy_contracts.scene import OutrageLevel
from strategy_contracts.terms import TributeTerm

SCENE_ID = UUID("11111111-1111-1111-1111-111111111111")


def test_relation_requires_sorted_distinct_pair() -> None:
    with pytest.raises(ValidationError):
        RelationState(
            faction_a="b", faction_b="a", status=RelationStatus.WAR, since_turn=0
        )
    with pytest.raises(ValidationError):
        RelationState(
            faction_a="a", faction_b="a", status=RelationStatus.WAR, since_turn=0
        )


def test_sorted_relation_is_accepted() -> None:
    relation = RelationState(
        faction_a="aa", faction_b="bb", status=RelationStatus.PEACE, since_turn=1
    )
    assert RelationState.model_validate_json(relation.model_dump_json()) == relation


def test_commitment_keeps_its_term_type_through_json() -> None:
    term = TributeTerm(payer_id="aa", payee_id="bb", gold_per_turn=5, duration_turns=6)
    commitment = CommitmentState(
        id="c1", term=term, start_turn=1, origin_scene_id=SCENE_ID
    )
    restored = CommitmentState.model_validate_json(commitment.model_dump_json())
    assert restored == commitment
    assert isinstance(restored.term, TributeTerm)


def test_remaining_diplomacy_models_round_trip() -> None:
    models = [
        TruceState(faction_a="aa", faction_b="bb", expires_turn=10),
        OathbreakerMark(faction_id="aa", since_turn=4),
        DiplomaticPlayState(
            id="p1", attacker_id="aa", defender_id="bb", stage="demand"
        ),
        WarState(
            id="w1",
            attacker_id="aa",
            defender_id="bb",
            participant_ids=["aa", "bb"],
            started_turn=2,
        ),
        OutrageState(faction_id="bb", level=OutrageLevel.ENRAGED, expires_turn=8),
        PrisonerState(
            id="pr1",
            held_by_id="aa",
            origin_faction_id="bb",
            kind=PrisonerKind.TROOPS,
            troop_count=40,
            origin_battle_id="battle_1",
            troops_by_type={"infantry": 40},
        ),
        EnvoyState(id="e1", from_faction_id="aa", at_faction_id="bb"),
    ]
    for model in models:
        assert type(model).model_validate_json(model.model_dump_json()) == model


def test_play_stage_outside_vocabulary_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DiplomaticPlayState.model_validate(
            {"id": "p1", "attacker_id": "aa", "defender_id": "bb", "stage": "ambush"}
        )


def test_claim_ground_requires_a_region() -> None:
    with pytest.raises(ValidationError):
        GroundState(
            id="ground_1",
            kind=GroundKind.CLAIM,
            holder_faction_id="aa",
            holder_leader_id="leader_aa",
            target_faction_id="bb",
            strength=100,
            since_turn=0,
            is_personal=False,
        )


def test_war_state_new_fields_default_to_empty() -> None:
    war = WarState(id="war_1", attacker_id="aa", defender_id="bb", started_turn=0)

    assert war.goals == []
    assert war.scored_battle_ids == []
    assert war.is_surprise is False
