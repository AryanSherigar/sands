from uuid import UUID

from app.engine.alliances.starting import seed_starting_alliances
from app.engine.diplomacy.grounds import seed_claim_grounds
from app.engine.ordering import canonicalize_lists
from app.engine.vassals.starting import seed_starting_vassalages
from app.engine.visibility.observations import record_visible_observations
from app.exceptions.world_exceptions import UnknownPlayerFactionError
from app.models.world_army import ArmyState
from app.models.world_character import (
    CommanderState,
    GovernorState,
    LeaderState,
    OpinionReason,
    OpinionState,
)
from app.models.world_clock import RngState, TurnClock
from app.models.world_diplomacy import RelationState
from app.models.world_faction import FactionState
from app.models.world_player import PlayerRuler
from app.models.world_region import ImprovementState, RegionState
from app.models.world_state import (
    CURRENT_AI_RULESET,
    CURRENT_ALLIANCE_RULESET,
    CURRENT_BATTLE_CONTROL_RULESET,
    CURRENT_COALITION_RULESET,
    CURRENT_DIPLOMACY_RULESET,
    CURRENT_ENDINGS_RULESET,
    CURRENT_EVENTS_RULESET,
    CURRENT_INTERNAL_RULESET,
    CURRENT_LOGISTICS_RULESET,
    CURRENT_OUTRAGE_RULESET,
    CURRENT_OVERTURE_RULESET,
    CURRENT_PEACE_RULESET,
    CURRENT_PRESSURE_RULESET,
    CURRENT_SUCCESSION_RULESET,
    CURRENT_SUMMARY_RULESET,
    CURRENT_VASSAL_RULESET,
    CURRENT_VISIBILITY_RULESET,
    WorldState,
)
from strategy_contracts.enums import TaxRate
from strategy_contracts.scenario import (
    FactionSetup,
    GrudgeSetup,
    LeaderSetup,
    RegionSetup,
    StrategyScenario,
)

GRUDGE_FADE_PER_TURN = 0
STARTING_WAR_EXHAUSTION = 0
STARTING_REPUTATION = 0
STARTING_IMPROVEMENT_TURNS = 0
STARTING_SINCE_TURN = 0


def _build_regions(scenario: StrategyScenario) -> dict[str, RegionState]:
    setups = {setup.region_id: setup for setup in scenario.starting.regions}
    claimants: dict[str, list[str]] = {}
    for claim in scenario.starting.claims:
        claimants.setdefault(claim.region_id, []).append(claim.faction_id)
    return {
        region.id: _build_region(
            setups.get(region.id) or RegionSetup(region_id=region.id),
            sorted(claimants.get(region.id, [])),
        )
        for region in sorted(scenario.map.regions, key=lambda item: item.id)
    }


def _build_region(setup: RegionSetup, claimant_ids: list[str]) -> RegionState:
    improvements = [
        ImprovementState(kind=kind, turns_remaining=STARTING_IMPROVEMENT_TURNS)
        for kind in setup.improvement_kinds
    ]
    return RegionState(
        id=setup.region_id,
        owner_id=setup.owner_id,
        population=setup.population,
        wealth=setup.wealth,
        manpower=setup.manpower,
        unrest=setup.unrest,
        garrison=setup.garrison,
        faith_id=setup.faith_id,
        improvements=improvements,
        governor_id=setup.governor_id,
        claimant_ids=claimant_ids,
    )


def _build_factions(
    scenario: StrategyScenario, player_faction_id: str
) -> dict[str, FactionState]:
    return {
        setup.id: _build_faction(scenario, setup, setup.id == player_faction_id)
        for setup in sorted(scenario.factions, key=lambda item: item.id)
    }


def _build_faction(
    scenario: StrategyScenario, setup: FactionSetup, is_player: bool
) -> FactionState:
    return FactionState(
        id=setup.id,
        leader_id=setup.leader_id,
        capital_region_id=setup.capital_region_id,
        treasury=setup.treasury,
        stability=setup.stability,
        war_exhaustion=STARTING_WAR_EXHAUSTION,
        reputation=STARTING_REPUTATION,
        tax_rate=TaxRate.NORMAL,
        orders_remaining=scenario.tuning.orders_per_turn,
        is_player=is_player,
    )


def _build_opinions(
    leader_id: str, grudges: list[GrudgeSetup]
) -> dict[str, OpinionState]:
    held = sorted(
        (grudge for grudge in grudges if grudge.holder_id == leader_id),
        key=lambda grudge: grudge.target_id,
    )
    return {
        grudge.target_id: OpinionState(
            target_id=grudge.target_id,
            reasons=[
                OpinionReason(
                    cause=grudge.reason,
                    value=grudge.opinion,
                    fade_per_turn=GRUDGE_FADE_PER_TURN,
                )
            ],
        )
        for grudge in held
    }


def _build_leader(setup: LeaderSetup, grudges: list[GrudgeSetup]) -> LeaderState:
    return LeaderState(
        id=setup.id,
        name=setup.name,
        faction_id=setup.faction_id,
        trait_ids=list(setup.trait_ids),
        ambition_ids=list(setup.ambition_ids),
        age=setup.age,
        opinions=_build_opinions(setup.id, grudges),
    )


def _build_armies(scenario: StrategyScenario) -> dict[str, ArmyState]:
    return {
        setup.id: ArmyState(
            id=setup.id,
            owner_id=setup.owner_id,
            troops=dict(setup.troops),
            commander_id=setup.commander_id,
            morale=setup.morale,
            location_id=setup.location_id,
        )
        for setup in sorted(scenario.starting.armies, key=lambda item: item.id)
    }


def _build_commanders(
    scenario: StrategyScenario, armies: dict[str, ArmyState]
) -> dict[str, CommanderState]:
    army_by_commander = {
        army.commander_id: army.id for army in armies.values() if army.commander_id
    }
    return {
        setup.id: CommanderState(
            id=setup.id,
            name=setup.name,
            faction_id=setup.faction_id,
            trait_ids=list(setup.trait_ids),
            is_important=setup.is_important,
            army_id=army_by_commander.get(setup.id),
        )
        for setup in sorted(scenario.commanders, key=lambda item: item.id)
    }


def _build_relations(scenario: StrategyScenario) -> list[RelationState]:
    return [
        RelationState(
            faction_a=min(setup.faction_a, setup.faction_b),
            faction_b=max(setup.faction_a, setup.faction_b),
            status=setup.status,
            since_turn=STARTING_SINCE_TURN,
        )
        for setup in scenario.starting.relations
    ]


def _build_leaders(scenario: StrategyScenario) -> dict[str, LeaderState]:
    return {
        setup.id: _build_leader(setup, scenario.starting.grudges)
        for setup in sorted(scenario.leaders, key=lambda item: item.id)
    }


def _build_governors(scenario: StrategyScenario) -> dict[str, GovernorState]:
    return {
        setup.id: GovernorState(
            id=setup.id,
            name=setup.name,
            region_id=setup.region_id,
            trait_ids=list(setup.trait_ids),
        )
        for setup in sorted(scenario.governors, key=lambda item: item.id)
    }


def new_world(
    scenario: StrategyScenario,
    playthrough_id: UUID,
    seed: int,
    player_faction_id: str,
    ruler: PlayerRuler,
) -> WorldState:
    if player_faction_id not in {setup.id for setup in scenario.factions}:
        raise UnknownPlayerFactionError(player_faction_id)
    armies = _build_armies(scenario)
    clock = TurnClock(
        turn=0,
        start_year=scenario.tuning.start_year,
        start_month=scenario.tuning.start_month,
    )
    world = WorldState(
        playthrough_id=playthrough_id,
        visibility_ruleset=CURRENT_VISIBILITY_RULESET,
        battle_control_ruleset=CURRENT_BATTLE_CONTROL_RULESET,
        internal_ruleset=CURRENT_INTERNAL_RULESET,
        endings_ruleset=CURRENT_ENDINGS_RULESET,
        logistics_ruleset=CURRENT_LOGISTICS_RULESET,
        summary_ruleset=CURRENT_SUMMARY_RULESET,
        events_ruleset=CURRENT_EVENTS_RULESET,
        diplomacy_ruleset=CURRENT_DIPLOMACY_RULESET,
        pressure_ruleset=CURRENT_PRESSURE_RULESET,
        peace_ruleset=CURRENT_PEACE_RULESET,
        alliance_ruleset=CURRENT_ALLIANCE_RULESET,
        vassal_ruleset=CURRENT_VASSAL_RULESET,
        coalition_ruleset=CURRENT_COALITION_RULESET,
        outrage_ruleset=CURRENT_OUTRAGE_RULESET,
        overture_ruleset=CURRENT_OVERTURE_RULESET,
        succession_ruleset=CURRENT_SUCCESSION_RULESET,
        ai_ruleset=CURRENT_AI_RULESET,
        clock=clock,
        rng=RngState(seed=seed),
        regions=_build_regions(scenario),
        factions=_build_factions(scenario, player_faction_id),
        leaders=_build_leaders(scenario),
        governors=_build_governors(scenario),
        commanders=_build_commanders(scenario, armies),
        armies=armies,
        relations=_build_relations(scenario),
        ruler=ruler,
    )
    seed_claim_grounds(world, scenario)
    seed_starting_alliances(world, scenario)
    seed_starting_vassalages(world, scenario)
    canonicalize_lists(world)
    record_visible_observations(world, scenario)
    return world
