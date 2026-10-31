from app.engine.ai.catalog import generate_candidates, legal_candidates
from app.engine.campaign import begin_campaign
from app.engine.hashing import world_hash
from app.engine.replay import replay_history
from app.models.battle_progress import OperationGuard
from app.models.replay import BeginCampaignReplayInput, ReplayStep, ReplayStepKind
from app.models.world_character import OpinionReason, OpinionState
from app.models.world_diplomacy import GroundState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.enums import RelationStatus

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYTHROUGH_ID,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    set_traits,
)


def _world(stance: str, traits: list[str] | None = None):
    world = make_world()
    set_traits(world, CAUTIOUS_RIVAL, traits or [])
    world.factions[CAUTIOUS_RIVAL].stance.option_id = stance
    return world


def _claim(world) -> None:
    world.grounds.append(
        GroundState(
            id="ground_90",
            kind=GroundKind.CLAIM,
            holder_faction_id=CAUTIOUS_RIVAL,
            holder_leader_id=world.factions[CAUTIOUS_RIVAL].leader_id,
            target_faction_id=WRATHFUL_RIVAL,
            region_id="fenwatch",
            strength=90,
            since_turn=0,
            is_personal=False,
        )
    )


def _status(world, first: str, second: str):
    low, high = sorted((first, second))
    return next(
        (
            item.status
            for item in world.relations
            if (item.faction_a, item.faction_b) == (low, high)
        ),
        None,
    )


def test_a_claim_and_a_martial_stance_lead_to_a_declared_war() -> None:
    world = _world("revenge_on_player")
    _claim(world)

    after = begin_campaign(world, SCENARIO).world

    assert _status(after, CAUTIOUS_RIVAL, WRATHFUL_RIVAL) == RelationStatus.WAR
    assert any(
        {war.attacker_id, war.defender_id} == {CAUTIOUS_RIVAL, WRATHFUL_RIVAL}
        for war in after.wars
    )


def test_a_hoarding_ruler_opens_a_demand_on_a_weaker_neighbour() -> None:
    after = begin_campaign(_world("turtle"), SCENARIO).world

    assert any(
        play.attacker_id == CAUTIOUS_RIVAL and play.defender_id == WRATHFUL_RIVAL
        for play in after.plays
    )


def test_a_cunning_ruler_with_a_grudge_forges_a_claim() -> None:
    world = _world("revenge_on_player", ["treacherous"])
    leader = world.factions[CAUTIOUS_RIVAL].leader_id
    harl = world.factions[WRATHFUL_RIVAL].leader_id
    world.leaders[leader].opinions[harl] = OpinionState(
        target_id=harl,
        reasons=[OpinionReason(cause="old feud", value=-40, fade_per_turn=0)],
    )

    after = begin_campaign(world, SCENARIO).world

    assert any(
        ground.is_forged and ground.holder_faction_id == CAUTIOUS_RIVAL
        for ground in after.grounds
    )


def test_a_courting_ruler_opens_talks() -> None:
    world = _world("court_ally")
    leader = world.factions[CAUTIOUS_RIVAL].leader_id
    harl = world.factions[WRATHFUL_RIVAL].leader_id
    world.leaders[leader].opinions[harl] = OpinionState(
        target_id=harl,
        reasons=[OpinionReason(cause="shared feast", value=30, fade_per_turn=0)],
    )

    after = begin_campaign(world, SCENARIO).world

    assert any(
        play.kind == "talks" and play.attacker_id == CAUTIOUS_RIVAL
        for play in after.plays
    )


def test_every_diplomacy_candidate_is_a_legal_order() -> None:
    world = _world("revenge_on_player", ["treacherous"])
    _claim(world)
    candidates = generate_candidates(world, SCENARIO, CAUTIOUS_RIVAL)

    legal = legal_candidates(world, SCENARIO, CAUTIOUS_RIVAL, candidates)

    kinds = {item.order.kind for item in legal}
    assert {"declare_war", "diplomatic_play", "call_negotiation"} <= kinds


def _begin_step(before, after) -> ReplayStep:
    guard = OperationGuard(
        operation_id="begin", expected_world_version=1, expected_turn=0, expected_wave=0
    )
    return ReplayStep(
        playthrough_id=PLAYTHROUGH_ID,
        sequence=1,
        operation_id="begin",
        kind=ReplayStepKind.BEGIN_CAMPAIGN,
        input=BeginCampaignReplayInput(guard=guard, stances=[]),
        before_hash=world_hash(before),
        after_hash=world_hash(after),
        turn=0,
        wave=0,
    )


def test_replay_reproduces_a_diplomatic_turn() -> None:
    before = _world("revenge_on_player")
    _claim(before)
    after = begin_campaign(before.model_copy(deep=True), SCENARIO).world

    replayed = replay_history(before, SCENARIO, [_begin_step(before, after)])

    assert replayed.world_hash == world_hash(after)
