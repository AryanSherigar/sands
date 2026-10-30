from uuid import UUID

from app.models.world_army import ArmyState
from app.models.world_clock import RngState, TurnClock
from app.models.world_diplomacy import RelationState
from app.models.world_faction import FactionState
from app.models.world_player import PlayerRuler
from app.models.world_region import RegionState
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus, TaxRate, TroopType

PLAYTHROUGH_ID = UUID("33333333-3333-3333-3333-333333333333")


def make_region(region_id: str, owner_id: str) -> RegionState:
    return RegionState(
        id=region_id,
        owner_id=owner_id,
        population=500,
        wealth=40,
        manpower=60,
        unrest=10,
        garrison=30,
        faith_id="old_faith",
    )


def make_faction(faction_id: str, is_player: bool) -> FactionState:
    return FactionState(
        id=faction_id,
        leader_id=None,
        treasury=100,
        stability=60,
        war_exhaustion=0,
        reputation=0,
        tax_rate=TaxRate.NORMAL,
        orders_remaining=6,
        is_player=is_player,
    )


def make_relation(faction_a: str, faction_b: str) -> RelationState:
    return RelationState(
        faction_a=faction_a,
        faction_b=faction_b,
        status=RelationStatus.PEACE,
        since_turn=0,
    )


def make_world() -> WorldState:
    return WorldState(
        playthrough_id=PLAYTHROUGH_ID,
        clock=TurnClock(turn=0, start_year=1000, start_month=3),
        rng=RngState(seed=42),
        regions={
            "ashford": make_region("ashford", "house_ashford"),
            "carrow_vale": make_region("carrow_vale", "house_carrow"),
        },
        factions={
            "house_ashford": make_faction("house_ashford", is_player=False),
            "house_carrow": make_faction("house_carrow", is_player=True),
        },
        armies={
            "army_a": ArmyState(
                id="army_a",
                owner_id="house_ashford",
                troops={TroopType.INFANTRY: 100},
                morale=70,
                location_id="ashford",
            )
        },
        ruler=PlayerRuler(
            name="Valdren",
            trait_ids=["honorable", "cautious"],
            ambition_ids=["ambition_peace"],
        ),
    )
