from app.engine.vassals.registry import granted_share
from app.engine.vassals.signing import sign_vassalage
from app.models.world_army import ArmyState
from app.models.world_diplomacy import CommitmentState
from app.models.world_region import RegionIntel
from app.models.world_state import WorldState
from app.models.world_vassal import DemandState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import VassalTerm
from strategy_contracts.traits import TraitDefinition
from strategy_contracts.vassal import DemandKind

from tests.engine.peace.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
    set_war_relation,
)

SCENE_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_TRIBUTE_PERCENT = 20

__all__ = [
    "CAUTIOUS_RIVAL",
    "PLAYER",
    "SCENARIO",
    "SCENE_ID",
    "WRATHFUL_RIVAL",
    "add_vassalage",
    "add_war",
    "make_demand",
    "make_vassal_term",
    "make_world",
    "set_axes",
    "set_power",
    "set_unrest",
    "set_war_relation",
]


def make_vassal_term(
    overlord_id: str,
    vassal_id: str,
    tribute: int = DEFAULT_TRIBUTE_PERCENT,
    levy: int = 0,
    is_controlled: bool = False,
    has_garrison: bool = False,
    duration: int = 0,
) -> VassalTerm:
    return VassalTerm(
        overlord_id=overlord_id,
        vassal_id=vassal_id,
        tribute_share_percent=tribute,
        levy_share_percent=levy,
        is_foreign_policy_controlled=is_controlled,
        has_garrison_rights=has_garrison,
        duration_turns=duration,
    )


def add_vassalage(
    world: WorldState,
    overlord_id: str,
    vassal_id: str,
    tribute: int = DEFAULT_TRIBUTE_PERCENT,
    levy: int = 0,
    is_controlled: bool = False,
    has_garrison: bool = False,
    duration: int = 0,
) -> CommitmentState:
    term = make_vassal_term(
        overlord_id, vassal_id, tribute, levy, is_controlled, has_garrison, duration
    )
    sign_vassalage(world, SCENARIO, term, SCENE_ID)
    return world.commitments[-1]


def set_axes(
    world: WorldState, scenario: StrategyScenario, faction_id: str, **axes: int
) -> StrategyScenario:
    trait = TraitDefinition(id="test_profile", name="test profile", effects=axes)
    leader_id = world.factions[faction_id].leader_id
    assert leader_id is not None
    world.leaders[leader_id].trait_ids = [trait.id]
    return scenario.model_copy(update={"custom_traits": [trait]})


def set_power(
    world: WorldState,
    vassal_id: str,
    overlord_id: str,
    vassal_troops: int,
    overlord_troops: int,
) -> None:
    world.armies = {
        "army_vassal": ArmyState(
            id="army_vassal",
            owner_id=vassal_id,
            troops={"infantry": vassal_troops},
            morale=50,
            location_id=next(
                key
                for key, region in sorted(world.regions.items())
                if region.owner_id == vassal_id
            ),
        )
    }
    intel = {
        key: RegionIntel(
            last_seen_turn=0,
            owner_id=overlord_id,
            garrison_low=overlord_troops,
            garrison_high=overlord_troops,
        )
        for key, region in sorted(world.regions.items())
        if region.owner_id == overlord_id
    }
    world.factions[vassal_id].intel = dict(list(intel.items())[:1])


def set_unrest(world: WorldState, faction_id: str, unrest: int) -> None:
    for region in world.regions.values():
        if region.owner_id == faction_id:
            region.unrest = unrest


def make_demand(
    commitment,
    kind: DemandKind = DemandKind.TRIBUTE,
    amount: int = 60,
    demand_id: str = "demand_1",
    turn: int = 0,
) -> DemandState:
    term = commitment.term
    return DemandState(
        id=demand_id,
        vassalage_id=commitment.id,
        overlord_id=term.overlord_id,
        vassal_id=term.vassal_id,
        kind=kind,
        amount=amount,
        granted=granted_share(commitment, kind),
        issued_turn=turn,
        deadline_turn=turn + 1,
    )
