from app.engine.succession.health import death_per_mille, health_band
from app.engine.succession.heirs import find_heir_setup
from app.models.api_world_view import (
    HeirView,
    RulerHealthView,
    SuccessionCrisisView,
    SuccessionView,
)
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario


def _ruler_health(
    world: WorldState, scenario: StrategyScenario, faction_id: str
) -> RulerHealthView | None:
    faction = world.factions.get(faction_id)
    if faction is None or not faction.leader_id:
        return None
    leader = world.leaders.get(faction.leader_id)
    if leader is None:
        return None
    return RulerHealthView(
        age=leader.age,
        health_band=health_band(leader, scenario),
        death_chance_per_mille=death_per_mille(leader, scenario),
    )


def _heir_view(
    world: WorldState, scenario: StrategyScenario, faction_id: str
) -> HeirView | None:
    faction = world.factions.get(faction_id)
    if faction is None or not faction.leader_id:
        return None
    heir_setup = find_heir_setup(scenario, faction.leader_id)
    if heir_setup is None:
        return None
    is_minor = heir_setup.age < scenario.tuning.succession.coming_of_age
    return HeirView(
        id=heir_setup.id,
        name=heir_setup.name,
        age=heir_setup.age,
        trait_ids=list(heir_setup.trait_ids),
        is_minor=is_minor,
    )


def _crisis_view(world: WorldState, faction_id: str) -> SuccessionCrisisView | None:
    crisis = next(
        (c for c in world.succession.crises if c.faction_id == faction_id), None
    )
    if crisis is None:
        return None
    regent = world.leaders.get(crisis.regent_id)
    regent_name = regent.name if regent is not None else "Regent"
    return SuccessionCrisisView(
        is_active=True,
        regent_name=regent_name,
        ends_turn=crisis.ends_turn,
    )


def project_succession(
    world: WorldState, scenario: StrategyScenario, faction_id: str
) -> SuccessionView | None:
    if not world.succession_ruleset:
        return None
    return SuccessionView(
        ruler_health=_ruler_health(world, scenario, faction_id),
        heir=_heir_view(world, scenario, faction_id),
        crisis=_crisis_view(world, faction_id),
    )
