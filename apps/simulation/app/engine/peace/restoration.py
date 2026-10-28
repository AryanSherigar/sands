from app.engine.diplomacy.events import diplomacy_event
from app.engine.peace.truces import breach_agreements
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_diplomacy import TruceState
from app.models.world_events import EventLogEntry
from app.models.world_peace import TreatyLapse
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario

TREATY_RENEWED = "treaty_renewed"
TREATY_REPUDIATED = "treaty_repudiated"


def find_lapse(world: WorldState, truce_id: str) -> TreatyLapse:
    lapse = next(
        (item for item in world.peace.lapses if item.truce_id == truce_id), None
    )
    if lapse is None:
        raise CampaignProgressError("treaty has not lapsed", "no_lapse", 422)
    return lapse


def find_truce(world: WorldState, truce_id: str) -> TruceState:
    truce = next((item for item in world.truces if item.id == truce_id), None)
    if truce is None:
        raise CampaignProgressError("unknown treaty", "no_lapse", 422)
    return truce


def other_party(truce: TruceState, faction_id: FactionId) -> FactionId:
    return truce.faction_b if faction_id == truce.faction_a else truce.faction_a


def restore_treaty(
    world: WorldState,
    scenario: StrategyScenario,
    truce_id: str,
    renewer_id: FactionId,
) -> list[EventLogEntry]:
    """Put a lapsed treaty back at its original tier once both sides have agreed."""
    lapse = find_lapse(world, truce_id)
    truce = find_truce(world, truce_id)
    other_id = other_party(truce, renewer_id)
    truce.tier = lapse.original_tier
    length = scenario.tuning.peace.tier_turns[truce.tier]
    truce.expires_turn = world.clock.turn + length if length else 0
    world.peace.lapses = [item for item in world.peace.lapses if item is not lapse]
    return [diplomacy_event(TREATY_RENEWED, [truce.id, renewer_id, other_id])]


def repudiate_treaty(
    world: WorldState,
    scenario: StrategyScenario,
    truce_id: str,
    faction_id: FactionId,
) -> list[EventLogEntry]:
    """A resentful heir breaks the lapsed treaty at a reduced breach cost."""
    find_lapse(world, truce_id)
    truce = find_truce(world, truce_id)
    other_id = other_party(truce, faction_id)
    percent = scenario.tuning.peace.repudiation_cost_percent
    events = breach_agreements(world, scenario, faction_id, other_id, percent)
    world.peace.lapses = [i for i in world.peace.lapses if i.truce_id != truce_id]
    return [*events, diplomacy_event(TREATY_REPUDIATED, [truce_id, faction_id])]
