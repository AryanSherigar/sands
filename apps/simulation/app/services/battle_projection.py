from app.engine.battles.reconnaissance import contact_strength
from app.exceptions.command_exceptions import CommandError
from app.models.api_battle import BattlePage
from app.models.battle_progress import CampaignState
from app.models.world_battle import (
    BattleState,
    BattleStatus,
    BattleView,
    ExchangeReceipt,
    ExchangeReport,
)
from strategy_contracts.enums import TroopType


def battle_page(state: CampaignState, after_id: str, limit: int) -> BattlePage:
    ordered = sorted(
        state.battles,
        key=lambda battle: (battle.status == BattleStatus.RESOLVED, battle.id),
    )
    start = battle_cursor(state, ordered, after_id)
    items = ordered[start : start + limit]
    next_cursor = None
    if start + limit < len(ordered):
        next_cursor = f"{state.world_version}:{items[-1].id}"
    return BattlePage(
        world_version=state.world_version, items=items, next_after_id=next_cursor
    )


def battle_cursor(
    state: CampaignState, ordered: list[BattleView], after_id: str
) -> int:
    if not after_id:
        return 0
    version, separator, identity = after_id.partition(":")
    if not separator or not version.isdecimal():
        raise CommandError("invalid battle cursor", "invalid_cursor", 422)
    if int(version) != state.world_version:
        raise CommandError("battle cursor is stale", "stale_cursor", 409)
    for index, battle in enumerate(ordered):
        if battle.id == identity:
            return index + 1
    raise CommandError("invalid battle cursor", "invalid_cursor", 422)


def exchange_report(
    receipt: ExchangeReceipt, battle: BattleState, observer: str
) -> ExchangeReport:
    own_ids = set(battle.contingents[observer].army_ids)
    losses = {
        troop: sum(
            item.combat_losses.get(troop, 0)
            + item.pursuit_losses.get(troop, 0)
            + item.captives.get(troop, 0)
            for item in receipt.accounting
            if item.army_id in own_ids
        )
        for troop in TroopType
    }
    enemy_ids = {
        army
        for contingent in battle.contingents.values()
        if contingent.side != battle.contingents[observer].side
        for army in contingent.army_ids
    }
    enemy_size = sum(
        sum(item.survivors.values())
        for item in receipt.accounting
        if item.army_id in enemy_ids
    )
    return ExchangeReport(
        battle_id=receipt.battle_id,
        campaign_turn=receipt.campaign_turn,
        exchange_index=receipt.exchange_index,
        total_exchange=receipt.total_exchange,
        own_losses={troop: count for troop, count in losses.items() if count},
        opponent_strength=contact_strength(enemy_size),
        outcome=receipt.outcome,
    )
