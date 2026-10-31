import pytest
from app.engine.vassals.commands import apply_vassal_order, validate_vassal_order
from app.engine.vassals.registry import vassalage_of
from app.exceptions.command_exceptions import CommandError
from app.models.orders import AnnexVassalOrder
from app.models.world_diplomacy import CommitmentStatus, WarSide
from app.models.world_state import WorldState

from tests.engine.alliances.builders import add_alliance
from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_vassalage,
    add_war,
    make_demand,
    make_world,
)

TUNING = SCENARIO.tuning.vassal


def _ready_world() -> tuple[WorldState, str]:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    war = add_war(world, attacker_id=PLAYER, defender_id=WRATHFUL_RIVAL)
    war.war_score_attacker = TUNING.annex_min_score
    world.factions[PLAYER].stability = TUNING.annex_min_stability
    return world, commitment.id


def _order(vassalage_id: str, faction: str = PLAYER) -> AnnexVassalOrder:
    return AnnexVassalOrder(faction_id=faction, vassalage_id=vassalage_id)


def _reason(world: WorldState, order: AnnexVassalOrder) -> str:
    with pytest.raises(CommandError) as refused:
        validate_vassal_order(world, SCENARIO, order)
    return refused.value.code


def _owned_by(world: WorldState, faction_id: str) -> list[str]:
    return sorted(k for k, r in world.regions.items() if r.owner_id == faction_id)


def test_ready_world_validates() -> None:
    world, commitment_id = _ready_world()

    validate_vassal_order(world, SCENARIO, _order(commitment_id))


def test_unknown_vassalage_and_non_overlord_are_rejected() -> None:
    world, commitment_id = _ready_world()

    assert _reason(world, _order("commitment_99")) == "unknown_vassalage"
    assert _reason(world, _order(commitment_id, WRATHFUL_RIVAL)) == "not_overlord"


def test_low_score_is_rejected() -> None:
    world, commitment_id = _ready_world()
    world.wars[0].war_score_attacker = TUNING.annex_min_score - 1

    assert _reason(world, _order(commitment_id)) == "score_too_low"


def test_low_stability_is_rejected() -> None:
    world, commitment_id = _ready_world()
    world.factions[PLAYER].stability = TUNING.annex_min_stability - 1

    assert _reason(world, _order(commitment_id)) == "stability_too_low"


def test_pending_demand_blocks_annexation() -> None:
    world, commitment_id = _ready_world()
    commitment = next(c for c in world.commitments if c.id == commitment_id)
    world.vassal.demands.append(make_demand(commitment))

    assert _reason(world, _order(commitment_id)) == "demand_pending"


def test_annexation_transfers_all_regions_and_destroys_the_vassal() -> None:
    world, commitment_id = _ready_world()
    taken = _owned_by(world, CAUTIOUS_RIVAL)
    held = _owned_by(world, PLAYER)

    events = apply_vassal_order(world, SCENARIO, _order(commitment_id))

    assert _owned_by(world, CAUTIOUS_RIVAL) == []
    assert _owned_by(world, PLAYER) == sorted(held + taken)
    assert world.factions[CAUTIOUS_RIVAL].is_destroyed
    assert vassalage_of(world, CAUTIOUS_RIVAL) is None
    assert "vassal_annexed" in [event.kind for event in events]


def test_annexation_records_region_ids_and_wealth_for_coalitions() -> None:
    world, commitment_id = _ready_world()
    taken = _owned_by(world, CAUTIOUS_RIVAL)
    wealth = sum(world.regions[r].wealth for r in taken)

    apply_vassal_order(world, SCENARIO, _order(commitment_id))

    [record] = world.vassal.annexations
    assert (record.overlord_id, record.vassal_id) == (PLAYER, CAUTIOUS_RIVAL)
    assert record.region_ids == taken
    assert record.wealth == wealth
    assert record.turn == world.clock.turn


def test_annexation_clears_calls_consents_and_standing() -> None:
    world, commitment_id = _ready_world()
    commitment = next(c for c in world.commitments if c.id == commitment_id)
    add_alliance(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)
    world.vassal.garrison_until[commitment.id] = 9

    apply_vassal_order(world, SCENARIO, _order(commitment_id))

    assert world.vassal.garrison_until == {}
    ally = next(
        c
        for c in world.commitments
        if c.id != commitment_id and c.term.kind == "alliance"
    )
    assert ally.status is CommitmentStatus.EXPIRED


def test_annexed_vassal_leaves_wars_cleanly() -> None:
    world, commitment_id = _ready_world()
    joined = add_war(world, WRATHFUL_RIVAL, PLAYER, war_id="war_2")
    joined.participant_ids.append(CAUTIOUS_RIVAL)
    joined.side_by_faction[CAUTIOUS_RIVAL] = WarSide.DEFENDER
    own = add_war(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL, war_id="war_3")

    apply_vassal_order(world, SCENARIO, _order(commitment_id))

    assert CAUTIOUS_RIVAL not in joined.participant_ids
    assert CAUTIOUS_RIVAL not in joined.side_by_faction
    assert own.id not in [war.id for war in world.wars]


def test_annexation_charges_no_breach() -> None:
    world, commitment_id = _ready_world()
    reputation = world.factions[PLAYER].reputation

    apply_vassal_order(world, SCENARIO, _order(commitment_id))

    taken = len(world.vassal.annexations[0].region_ids)
    conquest_cost = SCENARIO.tuning.coalition.conquest_reputation_cost
    assert world.oathbreakers == []
    assert world.factions[PLAYER].reputation == reputation - taken * conquest_cost


def test_annexation_records_conquests_and_raises_threat() -> None:
    from app.engine.coalitions.threat import compute_threat

    world, commitment_id = _ready_world()
    regions = _owned_by(world, CAUTIOUS_RIVAL)
    before_records = len(world.coalition.conquests)
    before_threat = compute_threat(world, SCENARIO, PLAYER).value

    apply_vassal_order(world, SCENARIO, _order(commitment_id))

    added = world.coalition.conquests[before_records:]
    assert len(added) == len(regions)
    assert {record.faction_id for record in added} == {PLAYER}
    assert compute_threat(world, SCENARIO, PLAYER).value > before_threat
