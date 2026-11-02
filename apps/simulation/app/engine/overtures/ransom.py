from app.engine.diplomacy.prisoners import ransom_price
from app.engine.negotiation import player_faction_id
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from app.models.world_peace import RansomCounter
from app.models.world_state import CAPTIVITY_RULESET, WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario


def is_ransom_active(world: WorldState) -> bool:
    return world.peace_ruleset >= CAPTIVITY_RULESET and world.treaty_ruleset >= 1


def _priority(prisoner: PrisonerState) -> tuple[int, str]:
    is_noble = prisoner.kind is PrisonerKind.CHARACTER
    return (0 if is_noble else 1, prisoner.id)


def affordable_captives(
    world: WorldState, scenario: StrategyScenario, holder_id: FactionId
) -> list[PrisonerState]:
    """The player's captives held by `holder_id`, nobles first, as many as the treasury can ransom."""
    player_id = player_faction_id(world)
    held = sorted(
        (
            item
            for item in world.prisoners
            if item.held_by_id == holder_id and item.origin_faction_id == player_id
        ),
        key=_priority,
    )
    budget = world.factions[player_id].treasury
    chosen: list[PrisonerState] = []
    for prisoner in held:
        price = ransom_price(prisoner, scenario.tuning.peace)
        if price > budget:
            continue
        budget -= price
        chosen.append(prisoner)
    return chosen


def has_ransomable_captives(
    world: WorldState, scenario: StrategyScenario, holder_id: FactionId
) -> bool:
    return bool(affordable_captives(world, scenario, holder_id))


def _is_counter_live(world: WorldState, counter: RansomCounter, expiry: int) -> bool:
    prisoner = next((p for p in world.prisoners if p.id == counter.prisoner_id), None)
    origin = world.factions.get(counter.origin_id)
    if prisoner is None or origin is None or origin.is_destroyed:
        return False
    is_same_pair = (prisoner.held_by_id, prisoner.origin_faction_id) == (
        counter.holder_id,
        counter.origin_id,
    )
    return is_same_pair and world.clock.turn - counter.turn <= expiry


def prune_ransom_counters(world: WorldState, scenario: StrategyScenario) -> None:
    expiry = scenario.tuning.peace.ransom_counter_expiry_turns
    world.peace.ransom_counters = [
        item
        for item in world.peace.ransom_counters
        if _is_counter_live(world, item, expiry)
    ]


def pending_counter(world: WorldState, faction_id: FactionId) -> RansomCounter | None:
    return next(
        (item for item in world.peace.ransom_counters if item.origin_id == faction_id),
        None,
    )
