from app.engine.diplomacy.prisoners import execute_prisoner, release_prisoner
from app.engine.negotiation import player_faction_id
from app.engine.pressure.captivity import captive_drain
from app.engine.pressure.wars import find_war
from app.engine.pressure.weariness import is_war_weary
from app.engine.trait_axes import axis_totals
from app.models.world_diplomacy import PrisonerState
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.traits import TraitAxis

CRUELTY_WEIGHT = 2


def _ruler_totals(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> dict[TraitAxis, int] | None:
    leader = world.leaders.get(world.factions[faction_id].leader_id or "")
    return None if leader is None else dict(axis_totals(leader, scenario))


def _cruelty_score(totals: dict[TraitAxis, int]) -> int:
    drive = CRUELTY_WEIGHT * totals.get(TraitAxis.CRUELTY, 0)
    return drive + totals.get(TraitAxis.PRIDE, 0) + totals.get(TraitAxis.AGGRESSION, 0)


def _mercy_score(totals: dict[TraitAxis, int]) -> int:
    return (
        totals.get(TraitAxis.HONOR, 0)
        + totals.get(TraitAxis.TRUST, 0)
        - totals.get(TraitAxis.CRUELTY, 0)
    )


def _is_calculating(totals: dict[TraitAxis, int]) -> bool:
    return totals.get(TraitAxis.CUNNING, 0) + totals.get(TraitAxis.GREED, 0) > 0


def _is_leverage_working(
    world: WorldState, scenario: StrategyScenario, totals: dict[TraitAxis, int]
) -> bool:
    player_id = player_faction_id(world)
    drain = captive_drain(world, scenario, player_id)
    return _is_calculating(totals) and drain >= (
        scenario.tuning.peace.npc_leverage_hold_drain
    )


def _held_turns(world: WorldState, prisoner: PrisonerState) -> int:
    since = prisoner.held_since_turn
    return 0 if since is None else world.clock.turn - since


def _oldest_captive(
    world: WorldState, holder_id: FactionId, player_id: FactionId
) -> PrisonerState | None:
    held = [
        item
        for item in world.prisoners
        if item.held_by_id == holder_id and item.origin_faction_id == player_id
    ]
    held.sort(key=lambda item: (item.held_since_turn or 0, item.id))
    return held[0] if held else None


def _is_mercy_timely(
    world: WorldState, scenario: StrategyScenario, holder_id: FactionId
) -> bool:
    player_id = player_faction_id(world)
    if find_war(world, holder_id, player_id) is None:
        return True
    return is_war_weary(world, scenario, holder_id)


def _decide(
    world: WorldState,
    scenario: StrategyScenario,
    holder_id: FactionId,
    captive: PrisonerState,
) -> list[EventLogEntry]:
    tuning = scenario.tuning.peace
    totals = _ruler_totals(world, scenario, holder_id)
    if totals is None:
        return []
    if _is_leverage_working(world, scenario, totals):
        return []
    held = _held_turns(world, captive)
    is_cruel = _cruelty_score(totals) >= tuning.npc_execute_cruelty_line
    if is_cruel and held >= tuning.npc_execute_min_hold_turns:
        return execute_prisoner(world, tuning, captive)
    is_merciful = _mercy_score(totals) >= tuning.npc_release_mercy_line
    is_ripe = held >= tuning.npc_release_min_hold_turns
    if is_merciful and is_ripe and _is_mercy_timely(world, scenario, holder_id):
        return release_prisoner(world, tuning, scenario, captive)
    return []


def act_on_player_captives(
    world: WorldState, scenario: StrategyScenario
) -> list[EventLogEntry]:
    """Each NPC holding the player's people may execute or release the one held longest."""
    player_id = player_faction_id(world)
    events: list[EventLogEntry] = []
    holders = sorted({item.held_by_id for item in world.prisoners} - {player_id})
    for holder_id in holders:
        captive = _oldest_captive(world, holder_id, player_id)
        if captive is not None:
            events += _decide(world, scenario, holder_id, captive)
    return events
