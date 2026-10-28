from app.models.world_events import EventCause, EventLogEntry, PhaseName, StateChange
from strategy_contracts.ids import ArmyId, EntityId, FactionId, RegionId

ORDER_REJECTED = "economy_order_rejected"
TAX_RATE_SET = "tax_rate_set"
PAY_SET = "pay_set"
LOAN_TAKEN = "loan_taken"
DEFAULT_DECLARED = "default_declared"
ARMY_RAISED = "army_raised"
ARMY_DISBANDED = "army_disbanded"
INCOME_COLLECTED = "income_collected"
UNREST_DRIFTED = "unrest_drifted"
MANPOWER_REFILLED = "manpower_refilled"
INTEREST_PAID = "loan_interest_paid"
UPKEEP_PAID = "upkeep_paid"
ARMY_UNPAID = "army_unpaid"
ARMY_RESTED = "army_rested"
ARMY_DESERTED = "army_deserted"
ARMY_DISSOLVED = "army_dissolved"
SHORTFALL_RESOLVED = "shortfall_resolved"
FACTION_DEFAULTED = "faction_defaulted"
LOAN_REPAID = "loan_repaid"
LOAN_OVERDUE = "loan_overdue"
CREDIT_RECOVERED = "credit_recovered"
INCOME_PREFIX = "income_"
UPKEEP_PREFIX = "upkeep_"
GAIN_PREFIX = "gain_"
LOST_PREFIX = "lost_"
LEVY_PREFIX = "levy_"


def _entry(
    kind: str,
    subject_ids: list[EntityId],
    inputs: dict[str, int],
    changes: list[StateChange],
    summary_key: str | None = None,
) -> EventLogEntry:
    cause = EventCause(
        summary_key=summary_key or kind, subject_ids=subject_ids, inputs=inputs
    )
    return EventLogEntry(
        seq=0, turn=0, phase=PhaseName.ECONOMY, kind=kind, cause=cause, changes=changes
    )


def order_rejected(subject_id: EntityId, reason: str) -> EventLogEntry:
    return _entry(
        ORDER_REJECTED, [subject_id], {}, [], summary_key=f"{ORDER_REJECTED}_{reason}"
    )


def tax_rate_set(faction_id: FactionId, before: str, after: str) -> EventLogEntry:
    change = StateChange(
        path=f"factions.{faction_id}.tax_rate", before=before, after=after
    )
    return _entry(TAX_RATE_SET, [faction_id], {}, [change])


def pay_set(army_id: ArmyId, before: str, after: str) -> EventLogEntry:
    change = StateChange(path=f"armies.{army_id}.pay_level", before=before, after=after)
    return _entry(PAY_SET, [army_id], {}, [change])


def loan_taken(
    faction_id: FactionId,
    requested: int,
    granted: int,
    interest_percent: int,
    change: StateChange,
    summary_key: str,
) -> EventLogEntry:
    inputs = {
        "requested": requested,
        "granted": granted,
        "interest_percent": interest_percent,
    }
    return _entry(LOAN_TAKEN, [faction_id], inputs, [change], summary_key)


def default_declared(faction_id: FactionId) -> EventLogEntry:
    return _entry(DEFAULT_DECLARED, [faction_id], {}, [])


def army_raised(
    faction_id: FactionId,
    army_id: ArmyId,
    region_id: RegionId,
    troops: dict[str, int],
    recruit_cost: int,
    changes: list[StateChange],
) -> EventLogEntry:
    inputs = {f"{LEVY_PREFIX}{key}": value for key, value in troops.items()}
    inputs["recruit_cost"] = recruit_cost
    return _entry(ARMY_RAISED, [faction_id, army_id, region_id], inputs, changes)


def army_disbanded(
    faction_id: FactionId, army_id: ArmyId, returned: int, changes: list[StateChange]
) -> EventLogEntry:
    return _entry(
        ARMY_DISBANDED, [faction_id, army_id], {"manpower_returned": returned}, changes
    )


def income_collected(
    faction_id: FactionId,
    tax_percent: int,
    by_region: dict[RegionId, int],
    occupied_region_ids: tuple[RegionId, ...],
    change: StateChange,
) -> EventLogEntry:
    inputs = {"tax_percent": tax_percent, "regions_occupied": len(occupied_region_ids)}
    inputs |= {f"{INCOME_PREFIX}{key}": value for key, value in by_region.items()}
    subjects = [faction_id, *occupied_region_ids]
    return _entry(INCOME_COLLECTED, subjects, inputs, [change])


def unrest_drifted(
    faction_id: FactionId,
    drift: int,
    moved: dict[RegionId, int],
    changes: list[StateChange],
) -> EventLogEntry:
    inputs = {"tax_drift": drift, "regions_moved": len(moved)}
    return _entry(UNREST_DRIFTED, [faction_id], inputs, changes)


def manpower_refilled(
    faction_id: FactionId, gains: dict[RegionId, int], changes: list[StateChange]
) -> EventLogEntry:
    inputs = {f"{GAIN_PREFIX}{key}": value for key, value in gains.items()}
    return _entry(MANPOWER_REFILLED, [faction_id], inputs, changes)


def interest_paid(
    faction_id: FactionId, due: int, paid: int, change: StateChange | None
) -> EventLogEntry:
    inputs = {"interest_due": due, "interest_paid": paid, "capitalized": due - paid}
    return _entry(INTEREST_PAID, [faction_id], inputs, [change] if change else [])


def upkeep_paid(
    faction_id: FactionId,
    costs: dict[ArmyId, int],
    unpaid_army_ids: list[ArmyId],
    change: StateChange,
) -> EventLogEntry:
    inputs = {f"{UPKEEP_PREFIX}{key}": value for key, value in costs.items()}
    inputs["armies_unpaid"] = len(unpaid_army_ids)
    return _entry(UPKEEP_PAID, [faction_id, *unpaid_army_ids], inputs, [change])


def army_unpaid(
    army_id: ArmyId, unpaid_turns: int, morale_loss: int, change: StateChange
) -> EventLogEntry:
    inputs = {"unpaid_turns": unpaid_turns, "morale_loss": morale_loss}
    return _entry(ARMY_UNPAID, [army_id], inputs, [change])


def army_rested(army_id: ArmyId, gain: int, change: StateChange) -> EventLogEntry:
    return _entry(ARMY_RESTED, [army_id], {"morale_gain": gain}, [change])


def army_deserted(
    army_id: ArmyId, lost: dict[str, int], changes: list[StateChange]
) -> EventLogEntry:
    inputs = {f"{LOST_PREFIX}{key}": value for key, value in lost.items()}
    return _entry(ARMY_DESERTED, [army_id], inputs, changes)


def army_dissolved(army_id: ArmyId) -> EventLogEntry:
    return _entry(ARMY_DISSOLVED, [army_id], {}, [])


def shortfall_resolved(
    faction_id: FactionId, choice: str, shortfall: int, loan_granted: int
) -> EventLogEntry:
    inputs = {"shortfall": shortfall, "loan_granted": loan_granted}
    return _entry(SHORTFALL_RESOLVED, [faction_id], inputs, [], choice)


def faction_defaulted(
    faction_id: FactionId, strikes: int, change: StateChange
) -> EventLogEntry:
    return _entry(
        FACTION_DEFAULTED, [faction_id], {"credit_strikes": strikes}, [change]
    )


def loan_repaid(
    faction_id: FactionId, paid: int, remaining: int, change: StateChange
) -> EventLogEntry:
    inputs = {"principal_paid": paid, "principal_remaining": remaining}
    return _entry(LOAN_REPAID, [faction_id], inputs, [change])


def loan_overdue(
    faction_id: FactionId, principal: int, interest_percent: int
) -> EventLogEntry:
    inputs = {"principal": principal, "interest_percent": interest_percent}
    return _entry(LOAN_OVERDUE, [faction_id], inputs, [])


def credit_recovered(faction_id: FactionId, strikes: int) -> EventLogEntry:
    return _entry(CREDIT_RECOVERED, [faction_id], {"credit_strikes": strikes}, [])
