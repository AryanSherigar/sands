from app.engine.economy.armies import remove_army
from app.models.world_battle import (
    BattleContingent,
    BattleOutcome,
    BattleSide,
    BattleState,
    BattleStatus,
)
from app.models.world_diplomacy import RelationStatus
from app.models.world_region import OccupationState
from app.models.world_siege import SiegeState
from app.models.world_state import WorldState

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    make_world,
    run_phase,
)
from tests.engine.pressure.builders import add_war

TARGET_REGION = "carrow_vale"
TARGET_OWNER = CAUTIOUS_RIVAL
BESIEGER = PLAYER
BESIEGER_ARMY = "army_ashford_1"

__all__ = [
    "BESIEGER",
    "BESIEGER_ARMY",
    "SCENARIO",
    "TARGET_OWNER",
    "TARGET_REGION",
    "add_resolved_battle",
    "add_siege",
    "make_siege_world",
    "make_world",
    "occupy",
    "run_phase",
    "set_at_war",
]


def set_at_war(world: WorldState, first: str, second: str) -> None:
    pair = tuple(sorted((first, second)))
    for relation in world.relations:
        if (relation.faction_a, relation.faction_b) == pair:
            relation.status = RelationStatus.WAR
    add_war(world, attacker_id=first, defender_id=second)


def make_siege_world() -> WorldState:
    """Besieger army standing in an emptied enemy region, nations at war."""
    world = make_world()
    for army_id in [
        army.id for army in world.armies.values() if army.location_id == TARGET_REGION
    ]:
        remove_army(world, army_id)
    world.armies[BESIEGER_ARMY].location_id = TARGET_REGION
    set_at_war(world, BESIEGER, TARGET_OWNER)
    return world


def add_resolved_battle(
    world: WorldState,
    winner: str = BESIEGER,
    loser: str = TARGET_OWNER,
    region_id: str = TARGET_REGION,
    army_id: str = BESIEGER_ARMY,
    battle_id: str = "battle_1",
) -> BattleState:
    battle = BattleState(
        id=battle_id,
        region_id=region_id,
        attacker_army_ids=[army_id],
        defender_army_ids=[],
        attacker_lead_faction_id=winner,
        defender_lead_faction_id=loser,
        current_turn=world.clock.turn,
        status=BattleStatus.RESOLVED,
        outcome=BattleOutcome.ATTACKER_VICTORY,
        contingents={
            winner: BattleContingent(
                faction_id=winner,
                side=BattleSide.ATTACKER,
                army_ids=[army_id],
                entry_troops=sum(world.armies[army_id].troops.values()),
            ),
            loser: BattleContingent(
                faction_id=loser,
                side=BattleSide.DEFENDER,
                army_ids=[],
                entry_troops=0,
            ),
        },
    )
    world.battles.append(battle)
    return battle


def add_siege(world: WorldState, progress: int = 0) -> None:
    world.sieges.append(
        SiegeState(
            region_id=TARGET_REGION,
            besieger_id=BESIEGER,
            army_ids=[BESIEGER_ARMY],
            progress=progress,
        )
    )


def occupy(world: WorldState, hold_turns: int = 0) -> None:
    world.regions[TARGET_REGION].occupation = OccupationState(
        occupier_id=BESIEGER, siege_progress=100, hold_turns=hold_turns
    )
