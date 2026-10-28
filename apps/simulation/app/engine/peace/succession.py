from app.engine.diplomacy.events import diplomacy_event
from app.engine.negotiation import acceptance_range
from app.engine.peace.restoration import (
    find_lapse,
    find_truce,
    other_party,
    repudiate_treaty,
    restore_treaty,
)
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_diplomacy import TruceState
from app.models.world_events import EventLogEntry
from app.models.world_peace import TreatyLapse
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId, LeaderId
from strategy_contracts.scenario import StrategyScenario

TREATY_LAPSED = "treaty_lapsed"


def _is_already_lapsed(
    world: WorldState, truce: TruceState, leader_id: LeaderId
) -> bool:
    return any(
        lapse.truce_id == truce.id and lapse.leader_id == leader_id
        for lapse in world.peace.lapses
    )


def _lapse(
    world: WorldState,
    scenario: StrategyScenario,
    truce: TruceState,
    leader_id: LeaderId,
) -> EventLogEntry:
    assert truce.tier is not None
    tuning = scenario.tuning.peace
    world.peace.lapses.append(
        TreatyLapse(
            truce_id=truce.id,
            faction_a=truce.faction_a,
            faction_b=truce.faction_b,
            original_tier=truce.tier,
            leader_id=leader_id,
            turn=world.clock.turn,
        )
    )
    truce.tier = tuning.renewal_short_tier
    truce.expires_turn = world.clock.turn + tuning.tier_turns[truce.tier]
    truce.is_fragile = True
    world.peace.hostages = [
        item for item in world.peace.hostages if item.truce_id != truce.id
    ]
    return diplomacy_event(TREATY_LAPSED, [truce.id, truce.faction_a, truce.faction_b])


def leader_died(
    world: WorldState, scenario: StrategyScenario, leader_id: LeaderId
) -> list[EventLogEntry]:
    """Hook for the future death model: weaken every treaty the leader signed."""
    events: list[EventLogEntry] = []
    for truce in sorted(world.truces, key=lambda item: item.id):
        is_signatory = leader_id in truce.signatory_leader_ids
        if truce.tier is None or not is_signatory:
            continue
        if _is_already_lapsed(world, truce, leader_id):
            continue
        events.append(_lapse(world, scenario, truce, leader_id))
    return events


def renew_treaty(
    world: WorldState,
    scenario: StrategyScenario,
    truce_id: str,
    renewer_id: FactionId,
) -> list[EventLogEntry]:
    """The heir asks the counterpart to restore the original tier; accepted at an even edge."""
    find_lapse(world, truce_id)
    truce = find_truce(world, truce_id)
    other_id = other_party(truce, renewer_id)
    limits = acceptance_range(world, scenario, renewer_id, other_id)
    if limits.accept_at > 0:
        raise CampaignProgressError("renewal refused", "renewal_refused", 422)
    return restore_treaty(world, scenario, truce_id, renewer_id)


__all__ = ["leader_died", "renew_treaty", "repudiate_treaty", "restore_treaty"]
