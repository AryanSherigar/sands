from collections.abc import Sequence

from app.engine.battles.deployment import reconcile_deployments
from app.engine.battles.lifecycle import reconcile_battle_outcome
from app.engine.battles.state import (
    BattleDelta,
    ExchangeResult,
    RetreatProposal,
)
from app.engine.ordering import canonicalize_lists
from app.models.world_battle import (
    ContingentStatus,
)
from app.models.world_events import (
    MAX_CAMPAIGN_WAVES,
    EventCause,
    EventLogEntry,
    PhaseName,
    StateChange,
)
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.battle import BattleTuning
from strategy_contracts.enums import RelationStatus


def _apply_armies(world: WorldState, delta: BattleDelta) -> None:
    world.armies.update(
        {
            identity: army.model_copy(deep=True)
            for identity, army in delta.army_updates.items()
        }
    )
    for identity in delta.removed_army_ids:
        world.armies.pop(identity, None)
    world.commanders.update(
        {
            identity: commander.model_copy(deep=True)
            for identity, commander in delta.commander_updates.items()
        }
    )
    world.prisoners.extend(
        prisoner.model_copy(deep=True) for prisoner in delta.prisoners
    )


def _apply_delta(world: WorldState, delta: BattleDelta) -> None:
    world.battles = [
        delta.battle.model_copy(deep=True) if battle.id == delta.battle.id else battle
        for battle in world.battles
    ]
    _apply_armies(world, delta)
    updates = {
        command.id: command.model_copy(deep=True) for command in delta.command_updates
    }
    world.accepted_commands = [
        updates.get(command.id, command) for command in world.accepted_commands
    ]
    for field in (
        "recon_reports",
        "scout_missions",
        "scout_captures",
        "battle_intents",
    ):
        getattr(world, field).update(
            {
                identity: item.model_copy(deep=True)
                for identity, item in getattr(delta, field).items()
            }
        )


def _record_battle_losses(
    world: WorldState, result: ExchangeResult, owners: dict[str, str]
) -> None:
    for row in result.receipt.accounting:
        faction_id = owners.get(row.army_id)
        if faction_id is None:
            continue
        losses = sum(row.combat_losses.values()) + sum(row.pursuit_losses.values())
        losses += sum(row.captives.values())
        if losses:
            world.battle_losses[faction_id] = (
                world.battle_losses.get(faction_id, 0) + losses
            )


def _can_share(world: WorldState, faction_id: str, others: list[str]) -> bool:
    return not any(
        relation.status == RelationStatus.WAR
        and faction_id in (relation.faction_a, relation.faction_b)
        and any(
            other in (relation.faction_a, relation.faction_b) and other != faction_id
            for other in others
        )
        for relation in world.relations
    )


def _arbitrate(
    world: WorldState, result: ExchangeResult, claims: dict[str, list[str]]
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    for proposal in sorted(
        result.delta.retreat_proposals, key=lambda item: item.faction_id
    ):
        destination = next(
            (
                region_id
                for region_id in proposal.candidate_region_ids
                if _can_share(world, proposal.faction_id, claims.get(region_id, []))
            ),
            None,
        )
        events.append(_apply_destination(world, result, proposal, destination))
        if destination is not None:
            claims.setdefault(destination, []).append(proposal.faction_id)
    return events


def _apply_destination(
    world: WorldState,
    result: ExchangeResult,
    proposal: RetreatProposal,
    destination: str | None,
) -> EventLogEntry:
    battle = next(
        battle for battle in world.battles if battle.id == result.delta.battle.id
    )
    contingent = battle.contingents[proposal.faction_id]
    contingent.retreat_destination_id = destination
    if destination is None:
        contingent.status = (
            ContingentStatus.ROUTED if proposal.is_rout else ContingentStatus.FIGHTING
        )
    for army_id in proposal.army_ids:
        if army_id in world.armies:
            world.armies[army_id].location_id = destination or battle.region_id
    return _retreat_event(world, battle.id, proposal.faction_id, destination)


def _retreat_event(
    world: WorldState, battle_id: str, faction_id: str, destination: str | None
) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=world.clock.turn,
        phase=PhaseName.BATTLES,
        kind="battle_retreat_arbitrated",
        cause=EventCause(
            summary_key="battle.retreat_arbitrated", subject_ids=[battle_id, faction_id]
        ),
        changes=[
            StateChange(
                path=f"battles.{battle_id}.contingents.{faction_id}.retreat_destination_id",
                after=destination,
            )
        ],
    )


def _reconcile_outcome(
    world: WorldState, result: ExchangeResult, max_waves: int, tuning: BattleTuning
) -> None:
    battle = next(
        battle for battle in world.battles if battle.id == result.delta.battle.id
    )
    reconcile_deployments(world, battle, tuning)
    reconcile_battle_outcome(world, battle, max_waves)
    result.receipt.outcome = battle.outcome
    for event in result.events:
        if event.kind == "battle_exchange_resolved":
            event.is_major = battle.outcome is not None
            event.changes[0].after = battle.outcome.value if battle.outcome else None


def stamp_wave_events(
    world: WorldState, events: list[EventLogEntry]
) -> list[EventLogEntry]:
    sequence = world.counters.get(CounterKind.EVENT_SEQ, 0)
    stamped = [
        event.model_copy(update={"seq": sequence + index, "turn": world.clock.turn})
        for index, event in enumerate(events, 1)
    ]
    world.counters[CounterKind.EVENT_SEQ] = sequence + len(stamped)
    return stamped


def reduce_wave(
    world: WorldState,
    results: Sequence[ExchangeResult],
    max_waves: int = MAX_CAMPAIGN_WAVES,
    *,
    battle_tuning: BattleTuning | None = None,
) -> tuple[WorldState, list[EventLogEntry]]:
    """Reduce typed battle ownership only; full convenience worlds are never composed."""
    owned = world.model_copy(deep=True)
    tuning = battle_tuning or BattleTuning(max_exchanges_per_turn=max_waves)
    ordered = sorted(
        (result.model_copy(deep=True) for result in results),
        key=lambda result: result.delta.battle.id,
    )
    for result in ordered:
        owners = {army_id: army.owner_id for army_id, army in owned.armies.items()}
        if owned.internal_ruleset:
            _record_battle_losses(owned, result, owners)
        _apply_delta(owned, result.delta)
    owned.progress.completed_waves += 1
    events: list[EventLogEntry] = []
    claims: dict[str, list[str]] = {}
    for result in ordered:
        arbitration = _arbitrate(owned, result, claims)
        _reconcile_outcome(owned, result, max_waves, tuning)
        events.extend(result.events + arbitration)
    canonicalize_lists(owned)
    return owned, stamp_wave_events(owned, events)
