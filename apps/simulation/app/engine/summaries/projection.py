from uuid import NAMESPACE_URL, uuid5

from app.engine.outrage.ledger import OUTRAGE_REVEALED
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.summary import SummaryFact

FACTION_KINDS = frozenset(
    {
        "faction_war_pressure_changed",
        "regional_unrest_changed",
        "uprising_started",
        "uprising_resolved",
        "uprising_stage_changed",
        "uprising_flipped",
        "income_collected",
        "upkeep_paid",
        "loan_interest_paid",
        "loan_taken",
        "loan_repaid",
        "tax_rate_set",
    }
)
ARMY_KINDS = frozenset(
    {
        "army_supply_attrition",
        "army_supply_withdrawal",
        "army_supply_surrender",
        "army_supply_disband",
        "army_fatigue_recovered",
    }
)
SAFE_INPUTS = frozenset(
    {
        "wars",
        "battle_losses",
        "unrest",
        "pressure",
        "isolated",
        "winter",
        "recovery",
        "isolated_turns",
        "combat_losses",
        "pursuit_losses",
        "captives",
    }
)


def project_summary_fact(
    world: WorldState, event: EventLogEntry, previous: WorldState | None = None
) -> SummaryFact | None:
    player = next(
        (key for key, value in world.factions.items() if value.is_player), None
    )
    if player is None:
        return None
    subjects = set(event.cause.subject_ids)
    regions = {
        key for key, region in world.regions.items() if region.owner_id == player
    }
    armies = _own_armies(world, player) | _own_armies(previous, player)
    if event.kind.startswith("battle_"):
        return _battle_fact(world, event, player, armies)
    if event.kind in ARMY_KINDS and subjects and subjects <= armies:
        return _fact(world, event, [])
    if event.kind == OUTRAGE_REVEALED:
        return _outrage_fact(world, event, player)
    if event.kind not in FACTION_KINDS or player not in subjects:
        return None
    uprising_ids = {item.id for item in world.uprisings if item.faction_id == player}
    if previous is not None:
        uprising_ids |= {
            item.id for item in previous.uprisings if item.faction_id == player
        }
    if not subjects <= {player, *regions, *uprising_ids}:
        return None
    return _fact(world, event, sorted(subjects & regions))


def _outrage_fact(
    world: WorldState, event: EventLogEntry, player: str
) -> SummaryFact | None:
    others = [item for item in event.cause.subject_ids if item != player]
    if player not in event.cause.subject_ids or len(others) != 1:
        return None
    fact = _fact(world, event, [])
    fact.values["about_faction_id"] = others[0]
    return fact


def _own_armies(world: WorldState | None, player: str) -> set[str]:
    if world is None:
        return set()
    return {key for key, army in world.armies.items() if army.owner_id == player}


def _battle_fact(
    world: WorldState, event: EventLogEntry, player: str, armies: set[str]
) -> SummaryFact | None:
    battle = next(
        (item for item in world.battles if item.id in event.cause.subject_ids), None
    )
    if battle is None or player not in battle.contingents:
        return None
    if event.kind == "battle_exchange_resolved":
        fact = _fact(world, event, [battle.region_id])
        if battle.outcome is not None:
            fact.values["outcome"] = battle.outcome.value
        return fact
    if event.kind == "battle_army_accounted":
        own_ids = armies | set(battle.contingents[player].army_ids)
        if set(event.cause.subject_ids) <= {battle.id, *own_ids}:
            return _fact(world, event, [battle.region_id])
    return None


def _fact(world: WorldState, event: EventLogEntry, regions: list[str]) -> SummaryFact:
    return SummaryFact(
        event_id=uuid5(
            NAMESPACE_URL, f"{world.playthrough_id}:summary-event:{event.seq}"
        ),
        kind=event.kind,
        turn=event.turn,
        text_key=event.kind,
        region_ids=regions,
        values={
            key: value
            for key, value in event.cause.inputs.items()
            if key in SAFE_INPUTS
        },
    )
