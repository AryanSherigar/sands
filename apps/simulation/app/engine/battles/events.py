from app.engine.battles.state import ExchangeRun
from app.models.world_events import EventCause, EventLogEntry, PhaseName, StateChange


def exchange_events(run: ExchangeRun) -> list[EventLogEntry]:
    """Return local seq=0 events; only the global wave reducer allocates durable sequence IDs."""
    events = [_army_event(run, army_id) for army_id in sorted(run.accounting)]
    events.append(
        EventLogEntry(
            seq=0,
            turn=run.world.clock.turn,
            phase=PhaseName.BATTLES,
            kind="battle_exchange_resolved",
            is_major=run.battle.outcome is not None,
            cause=EventCause(
                summary_key="battle.exchange",
                subject_ids=[run.battle.id],
                inputs={"exchange": run.battle.total_exchanges},
            ),
            changes=[
                StateChange(
                    path=f"battles.{run.battle.id}.outcome",
                    after=run.battle.outcome.value if run.battle.outcome else None,
                )
            ],
        )
    )
    return events


def _army_event(run: ExchangeRun, army_id: str) -> EventLogEntry:
    row = run.accounting[army_id]
    return EventLogEntry(
        seq=0,
        turn=run.world.clock.turn,
        phase=PhaseName.BATTLES,
        kind="battle_army_accounted",
        cause=EventCause(
            summary_key="battle.army_accounting",
            subject_ids=[run.battle.id, army_id],
            inputs={
                "combat_losses": sum(row.combat_losses.values()),
                "pursuit_losses": sum(row.pursuit_losses.values()),
                "captives": sum(row.captives.values()),
            },
        ),
        changes=[
            StateChange(
                path=f"armies.{army_id}.troops",
                before=sum(row.before.values()),
                after=sum(row.survivors.values()),
            )
        ],
    )
