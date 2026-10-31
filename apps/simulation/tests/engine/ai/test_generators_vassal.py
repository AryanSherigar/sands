from app.engine.ai.generators.vassal import vassal_candidates
from app.models.orders import (
    AnnexVassalOrder,
    DemandFromVassalOrder,
    ReleaseVassalOrder,
)
from app.models.world_ai import AimState
from app.models.world_army import ArmyState
from app.models.world_region import RegionIntel
from app.models.world_vassal import VassalStanding
from strategy_contracts.stances import ScoreCategory
from strategy_contracts.vassal import DemandKind

from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_vassalage,
    add_war,
    make_world,
)

TUNING = SCENARIO.tuning.ai
OVERLORD = CAUTIOUS_RIVAL
VASSAL = WRATHFUL_RIVAL
OVERLORD_TROOPS = 1000
WEAK_GARRISON = 100
STRONG_GARRISON = 900
RICH = 1000


def _world(vassal_garrison: int = WEAK_GARRISON, vassal_id: str = VASSAL):
    world = make_world()
    commitment = add_vassalage(world, OVERLORD, vassal_id)
    world.factions[OVERLORD].treasury = RICH
    home = next(
        key
        for key, region in sorted(world.regions.items())
        if region.owner_id == OVERLORD
    )
    world.armies = {
        "army_overlord": ArmyState(
            id="army_overlord",
            owner_id=OVERLORD,
            troops={"infantry": OVERLORD_TROOPS},
            morale=50,
            location_id=home,
        )
    }
    held = next(
        key
        for key, region in sorted(world.regions.items())
        if region.owner_id == vassal_id
    )
    world.factions[OVERLORD].intel = {
        held: RegionIntel(
            last_seen_turn=0,
            owner_id=vassal_id,
            garrison_low=vassal_garrison,
            garrison_high=vassal_garrison,
        )
    }
    return world, commitment


def _orders(world, kind):
    return [
        item
        for item in vassal_candidates(world, SCENARIO, OVERLORD)
        if isinstance(item.order, kind)
    ]


def _aim(world, category: ScoreCategory) -> None:
    world.aims[OVERLORD] = AimState(
        category=category,
        chosen_turn=0,
        leader_id=world.factions[OVERLORD].leader_id,
        capital_held=True,
    )


def test_a_dominant_overlord_demands_a_modest_excess_in_tribute() -> None:
    world, commitment = _world()
    demands = _orders(world, DemandFromVassalOrder)
    assert len(demands) == 1
    order = demands[0].order
    assert order.vassalage_id == commitment.id
    assert order.demand_kind is DemandKind.TRIBUTE
    assert (
        order.amount
        == commitment.term.tribute_share_percent + TUNING.demand_step_percent
    )
    assert demands[0].base_score == TUNING.demand_vassal_bonus


def test_a_war_makes_the_demand_a_levy() -> None:
    world, _ = _world()
    add_war(world, attacker_id=OVERLORD, defender_id=PLAYER)
    order = _orders(world, DemandFromVassalOrder)[0].order
    assert order.demand_kind is DemandKind.LEVY


def test_a_vassal_strong_enough_to_rebel_is_not_squeezed() -> None:
    world, _ = _world(vassal_garrison=STRONG_GARRISON)
    assert _orders(world, DemandFromVassalOrder) == []


def test_a_player_vassal_is_left_alone() -> None:
    world, _ = _world(vassal_id=PLAYER)
    assert vassal_candidates(world, SCENARIO, OVERLORD) == []


def test_annexation_needs_a_conquest_aim() -> None:
    world, commitment = _world()
    assert _orders(world, AnnexVassalOrder) == []
    _aim(world, ScoreCategory.HOARD)
    assert _orders(world, AnnexVassalOrder) == []
    _aim(world, ScoreCategory.EXPAND)
    annexes = _orders(world, AnnexVassalOrder)
    assert [item.order.vassalage_id for item in annexes] == [commitment.id]
    assert annexes[0].base_score == TUNING.annex_bonus


def test_a_strong_vassal_is_not_annexed() -> None:
    world, _ = _world(vassal_garrison=STRONG_GARRISON)
    _aim(world, ScoreCategory.ATTACK)
    assert _orders(world, AnnexVassalOrder) == []


def test_a_restless_strong_vassal_is_released() -> None:
    world, commitment = _world(vassal_garrison=STRONG_GARRISON)
    world.vassal.standing.append(
        VassalStanding(vassalage_id=commitment.id, grievance=TUNING.release_grievance)
    )
    releases = _orders(world, ReleaseVassalOrder)
    assert [item.order.vassalage_id for item in releases] == [commitment.id]
    assert releases[0].category is ScoreCategory.BUILD


def test_a_content_vassal_is_kept() -> None:
    world, _ = _world(vassal_garrison=STRONG_GARRISON)
    assert _orders(world, ReleaseVassalOrder) == []


def test_a_broke_overlord_at_war_sheds_its_vassal() -> None:
    world, _ = _world()
    add_war(world, attacker_id=OVERLORD, defender_id=PLAYER)
    world.factions[OVERLORD].treasury = 0
    assert len(_orders(world, ReleaseVassalOrder)) == 1


def test_the_vassal_toggle_disables_the_generator() -> None:
    world, _ = _world()
    scenario = SCENARIO.model_copy(deep=True)
    scenario.toggles.is_ai_vassal_enabled = False
    assert vassal_candidates(world, scenario, OVERLORD) == []
