from collections.abc import Mapping
from dataclasses import dataclass

from app.engine.battles.exchange import resolve_exchange
from app.engine.battles.phase import active_battles
from app.engine.battles.policy import choose_instruction, select_intent
from app.engine.battles.reducer import reduce_wave
from app.engine.battles.state import ExchangeResult
from app.engine.battles.views import IntentBriefing, intent_briefing
from app.engine.commands.application import accept_command
from app.engine.commands.timing import require_window
from app.engine.hashing import world_hash
from app.engine.ordering import canonicalize_lists
from app.engine.outrage.effects import has_press_bias
from app.engine.summaries.triggers import evaluate_summary_triggers
from app.models.battle_command import Command
from app.models.battle_intelligence import BattleIntent
from app.models.world_battle import ExchangeReceipt, RetreatResolution
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.battle import BattleTuning
from strategy_contracts.scenario import StrategyScenario


@dataclass(frozen=True)
class WaveResult:
    world: WorldState
    events: list[EventLogEntry]
    receipts: list[ExchangeReceipt]
    is_complete: bool


def _npc_pairs(world: WorldState) -> list[tuple[str, str]]:
    return sorted(
        (faction_id, battle.id)
        for battle in active_battles(world)
        for faction_id in battle.contingents
        if not world.factions[faction_id].is_player
    )


def _select_candidate(
    briefing: IntentBriefing,
    tuning: BattleTuning,
    candidates: Mapping[str, BattleIntent],
    should_press: bool,
) -> BattleIntent:
    for _, candidate in sorted(candidates.items()):
        if (
            candidate.battle_id != briefing.battle.id
            or candidate.faction_id != briefing.faction_id
        ):
            continue
        selected = select_intent(briefing, tuning, candidate, should_press)
        if selected == candidate:
            return selected
    return select_intent(briefing, tuning, should_press=should_press)


def _reserve_npc(
    world: WorldState,
    scenario: StrategyScenario,
    command: Command,
    intent: BattleIntent,
) -> WorldState:
    identity = f"npc:{intent.id}:{command.kind}"
    return accept_command(
        world,
        scenario,
        command,
        command_id=identity,
        operation_id=identity,
        actor_id=f"npc:{command.faction_id}",
        faction_id=command.faction_id,
        expected_turn=world.clock.turn,
        expected_wave=world.progress.completed_waves + 1,
    ).world


def _npc_decisions(
    world: WorldState,
    scenario: StrategyScenario,
    candidates: Mapping[str, BattleIntent],
) -> tuple[WorldState, dict[str, BattleIntent]]:
    owned = world.model_copy(deep=True)
    selected: dict[str, BattleIntent] = {}
    for faction_id, battle_id in _npc_pairs(world):
        briefing = intent_briefing(world, battle_id, faction_id, scenario)
        if not briefing.battle.legal_commands:
            continue
        should_press = has_press_bias(world, scenario, faction_id)
        intent = _select_candidate(
            briefing, scenario.tuning.battle, candidates, should_press
        )
        selected[intent.id] = intent
        briefing.orders_remaining = owned.factions[faction_id].orders_remaining
        command = choose_instruction(briefing, intent.kind, scenario.tuning.battle)
        if command is not None:
            owned = _reserve_npc(owned, scenario, command, intent)
    canonicalize_lists(owned)
    return owned, selected


def advance_wave(
    world: WorldState,
    scenario: StrategyScenario,
    *,
    expected_turn: int,
    expected_wave: int,
    recorded_intents: Mapping[str, BattleIntent] | None = None,
) -> WaveResult:
    """Freeze global commands before exchanges; caller persists this wave atomically."""
    require_window(world, expected_turn, expected_wave)
    frozen, selected = _npc_decisions(world, scenario, recorded_intents or {})
    results = [
        resolve_exchange(
            frozen, battle.id, scenario, frozen.accepted_commands, selected
        )
        for battle in active_battles(frozen)
    ]
    reduced, events = _reduce_results(frozen, results, scenario)
    if reduced.summary_ruleset == 2:
        evaluate_summary_triggers(reduced, scenario, events, frozen)
    is_complete = (
        reduced.progress.completed_waves
        >= scenario.tuning.battle.max_exchanges_per_turn
        or not active_battles(reduced)
    )
    reduced.progress.waiting_reason = None if is_complete else "awaiting_commands"
    receipts = [_final_receipt(result, reduced) for result in results]
    return WaveResult(reduced, events, receipts, is_complete)


def _reduce_results(
    frozen: WorldState, results: list[ExchangeResult], scenario: StrategyScenario
) -> tuple[WorldState, list[EventLogEntry]]:
    return reduce_wave(
        frozen,
        results,
        scenario.tuning.battle.max_exchanges_per_turn,
        battle_tuning=scenario.tuning.battle,
    )


def _final_receipt(result: ExchangeResult, world: WorldState) -> ExchangeReceipt:
    battle = next(
        battle for battle in world.battles if battle.id == result.receipt.battle_id
    )
    retreats = [
        RetreatResolution(
            faction_id=proposal.faction_id,
            destination_id=battle.contingents[
                proposal.faction_id
            ].retreat_destination_id,
            has_succeeded=battle.contingents[proposal.faction_id].retreat_destination_id
            is not None,
        )
        for proposal in sorted(
            result.delta.retreat_proposals, key=lambda proposal: proposal.faction_id
        )
    ]
    return result.receipt.model_copy(
        update={
            "output_hash": world_hash(world),
            "outcome": battle.outcome,
            "retreats": retreats,
        }
    )
