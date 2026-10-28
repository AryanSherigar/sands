from collections import defaultdict
from collections.abc import Sequence

from app.models.api_turn import (
    BattleReport,
    BattleRoundReport,
    EconomyCategory,
    EconomyReportLine,
    ReportLine,
    TurnReport,
)
from app.models.world_battle import BattleState, ExchangeReceipt
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.enums import TroopType

BATTLE_EVENT_PREFIX = "battle_"
ECONOMY_CATEGORY_BY_KIND: dict[str, EconomyCategory] = {
    "income_collected": "tax",
    "upkeep_paid": "upkeep",
    "loan_interest_paid": "loan",
    "loan_taken": "loan",
    "loan_repaid": "loan",
}


def _treasury_delta(event: EventLogEntry, faction_id: str) -> int | None:
    path = f"factions.{faction_id}.treasury"
    deltas = [
        change.after - change.before
        for change in event.changes
        if change.path == path
        and isinstance(change.before, int)
        and isinstance(change.after, int)
    ]
    return sum(deltas) if deltas else None


def build_economy_lines(
    events: Sequence[EventLogEntry], faction_id: str
) -> list[EconomyReportLine]:
    lines: list[EconomyReportLine] = []
    for event in events:
        amount = _treasury_delta(event, faction_id)
        if amount is None:
            continue
        lines.append(
            EconomyReportLine(
                kind=event.kind,
                category=ECONOMY_CATEGORY_BY_KIND.get(event.kind, "other"),
                amount=amount,
                subject_ids=event.cause.subject_ids,
                inputs=event.cause.inputs,
            )
        )
    return lines


def _own_battles(world: WorldState, faction_id: str) -> dict[str, BattleState]:
    return {
        battle.id: battle
        for battle in world.battles
        if faction_id in battle.contingents
    }


def _sum_own_losses(
    receipts: Sequence[ExchangeReceipt], own_army_ids: set[str]
) -> dict[TroopType, int]:
    losses: dict[TroopType, int] = defaultdict(int)
    for receipt in receipts:
        for accounting in receipt.accounting:
            if accounting.army_id not in own_army_ids:
                continue
            for lost in (accounting.combat_losses, accounting.pursuit_losses):
                for troop_type, count in lost.items():
                    losses[troop_type] += count
    return dict(losses)


def _build_rounds(
    receipts: Sequence[ExchangeReceipt], own_army_ids: set[str]
) -> list[BattleRoundReport]:
    return [
        BattleRoundReport(
            total_exchange=receipt.total_exchange,
            own_losses=sum(_sum_own_losses([receipt], own_army_ids).values()),
        )
        for receipt in receipts
    ]


def build_battle_reports(
    receipts: Sequence[ExchangeReceipt], world: WorldState, faction_id: str
) -> list[BattleReport]:
    own_battles = _own_battles(world, faction_id)
    receipts_by_battle: dict[str, list[ExchangeReceipt]] = defaultdict(list)
    for receipt in receipts:
        if receipt.battle_id in own_battles:
            receipts_by_battle[receipt.battle_id].append(receipt)
    reports: list[BattleReport] = []
    for battle_id, battle_receipts in sorted(receipts_by_battle.items()):
        battle = own_battles[battle_id]
        contingent = battle.contingents[faction_id]
        reports.append(
            BattleReport(
                battle_id=battle_id,
                region_id=battle.region_id,
                outcome=battle_receipts[-1].outcome,
                own_side=contingent.side,
                exchanges=len(battle_receipts),
                own_losses=_sum_own_losses(battle_receipts, set(contingent.army_ids)),
                rounds=_build_rounds(battle_receipts, set(contingent.army_ids)),
            )
        )
    return reports


def _visible_subject_ids(world: WorldState, faction_id: str) -> set[str]:
    own_armies = {
        key for key, army in world.armies.items() if army.owner_id == faction_id
    }
    own_regions = {
        key for key, region in world.regions.items() if region.owner_id == faction_id
    }
    own_governors = {
        key
        for key, governor in world.governors.items()
        if governor.region_id in own_regions
    }
    return {faction_id} | own_armies | own_regions | own_governors


def _visible_events(
    events: Sequence[EventLogEntry], world: WorldState, faction_id: str
) -> list[EventLogEntry]:
    visible = _visible_subject_ids(world, faction_id)
    return [
        event
        for event in events
        if not event.kind.startswith(BATTLE_EVENT_PREFIX)
        and event.cause.subject_ids
        and set(event.cause.subject_ids) <= visible
    ]


def build_event_lines(
    events: Sequence[EventLogEntry], world: WorldState, faction_id: str
) -> list[ReportLine]:
    return [
        ReportLine(
            text_key=event.cause.summary_key,
            kind=event.kind,
            subject_ids=event.cause.subject_ids,
            cause=event.cause,
        )
        for event in _visible_events(events, world, faction_id)
    ]


def build_turn_report(
    turn: int,
    events: Sequence[EventLogEntry],
    receipts: Sequence[ExchangeReceipt],
    world: WorldState,
    faction_id: str,
) -> TurnReport:
    economy = build_economy_lines(events, faction_id)
    visible_events = _visible_events(events, world, faction_id)
    return TurnReport(
        turn=turn,
        net_gold=sum(line.amount for line in economy),
        economy=economy,
        battles=build_battle_reports(receipts, world, faction_id),
        lines=build_event_lines(events, world, faction_id),
        major_event_kinds=sorted(
            {event.kind for event in visible_events if event.is_major}
        ),
    )
