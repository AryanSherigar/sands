from dataclasses import dataclass

from app.engine.ai.standing import FULL_PERCENT, known_power_ratio
from app.engine.alliances.joining import join_war
from app.engine.alliances.refusal import refuse_call
from app.engine.diplomacy.events import diplomacy_event
from app.engine.opinion import opinion_of, shift_opinion
from app.engine.pressure.wars import side_of
from app.engine.trait_axes import axis_totals
from app.exceptions.command_exceptions import CommandError
from app.models.orders import AnswerCallOrder
from app.models.world_alliance import CallToArmsState
from app.models.world_character import LeaderState
from app.models.world_diplomacy import WarState
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.alliance import AllianceTuning
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.traits import TraitAxis

CALL_DECLINED = "call_declined"
BOTH_SIDES_CAUSE = "declined_for_other_side"
HTTP_UNPROCESSABLE = 422


@dataclass(frozen=True)
class CallAnswer:
    is_joining: bool
    reason_key: str


def _reject(reason: str) -> CommandError:
    return CommandError("order not possible", reason, HTTP_UNPROCESSABLE)


def _find_call(world: WorldState, call_id: str) -> CallToArmsState | None:
    return next((item for item in world.alliance.calls if item.id == call_id), None)


def _find_war(world: WorldState, war_id: str) -> WarState | None:
    return next((item for item in world.wars if item.id == war_id), None)


def validate_answer_call(world: WorldState, order: AnswerCallOrder) -> None:
    call = _find_call(world, order.call_id)
    if call is None:
        raise _reject("unknown_call")
    if call.ally_id != order.faction_id:
        raise _reject("not_ally")
    if world.clock.turn > call.deadline_turn:
        raise _reject("call_expired")


def _enemy_principal(war: WarState, call: CallToArmsState) -> str:
    is_attacker_side = side_of(war, call.caller_id) is side_of(war, war.attacker_id)
    return war.defender_id if is_attacker_side else war.attacker_id


def _temperament(leader: LeaderState, scenario: StrategyScenario) -> int:
    totals = axis_totals(leader, scenario)
    leaning = (
        totals[TraitAxis.HONOR]
        + totals[TraitAxis.TRUST]
        - totals[TraitAxis.CAUTION]
        - totals[TraitAxis.GREED]
    )
    return scenario.tuning.alliance.join_axis_weight * leaning


def _legitimacy(war: WarState, call: CallToArmsState, tuning: AllianceTuning) -> int:
    defensive = tuning.join_defensive_bonus if call.is_defensive else 0
    grounded = tuning.join_ground_bonus if war.ground_kind is not None else 0
    return defensive + grounded


def join_score_terms(
    world: WorldState, scenario: StrategyScenario, call: CallToArmsState
) -> dict[str, int]:
    tuning = scenario.tuning.alliance
    war = _find_war(world, call.war_id)
    assert war is not None
    leader = world.leaders[world.factions[call.ally_id].leader_id]
    caller_leader_id = world.factions[call.caller_id].leader_id
    ratio = known_power_ratio(
        world, scenario, call.ally_id, _enemy_principal(war, call)
    )
    return {
        "temperament": _temperament(leader, scenario),
        "opinion": opinion_of(leader, caller_leader_id) // tuning.join_opinion_divisor,
        "strength": (ratio - FULL_PERCENT) // tuning.join_strength_divisor,
        "legitimacy": _legitimacy(war, call, tuning),
    }


def npc_answer(
    world: WorldState, scenario: StrategyScenario, call: CallToArmsState
) -> CallAnswer:
    terms = join_score_terms(world, scenario, call)
    threshold = scenario.tuning.alliance.join_threshold
    dominant = max(sorted(terms), key=lambda name: abs(terms[name]))
    return CallAnswer(sum(terms.values()) >= threshold, dominant)


def _decline_for_other_side(
    world: WorldState, scenario: StrategyScenario, call: CallToArmsState
) -> list[EventLogEntry]:
    tuning = scenario.tuning.alliance
    shift_opinion(
        world,
        call.caller_id,
        call.ally_id,
        BOTH_SIDES_CAUSE,
        -tuning.both_sides_opinion_cost,
        tuning.opinion_fade_per_turn,
    )
    return [diplomacy_event(CALL_DECLINED, [call.war_id, call.ally_id, call.caller_id])]


def _remove_call(world: WorldState, call: CallToArmsState) -> None:
    world.alliance.calls = [item for item in world.alliance.calls if item.id != call.id]


def _decline_siblings(
    world: WorldState, scenario: StrategyScenario, joined: CallToArmsState
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    siblings = [
        item
        for item in sorted(world.alliance.calls, key=lambda item: item.id)
        if (item.war_id, item.ally_id) == (joined.war_id, joined.ally_id)
    ]
    for sibling in siblings:
        _remove_call(world, sibling)
        events += _decline_for_other_side(world, scenario, sibling)
    return events


def _answer_call(
    world: WorldState,
    scenario: StrategyScenario,
    call: CallToArmsState,
    is_joining: bool,
) -> list[EventLogEntry]:
    _remove_call(world, call)
    if not is_joining:
        return refuse_call(world, scenario, call)
    events = join_war(world, scenario, call)
    return events + _decline_siblings(world, scenario, call)


def apply_answer(
    world: WorldState, scenario: StrategyScenario, order: AnswerCallOrder
) -> list[EventLogEntry]:
    validate_answer_call(world, order)
    call = _find_call(world, order.call_id)
    assert call is not None
    return _answer_call(world, scenario, call, order.is_joining)


def _best_joining_call(
    world: WorldState, scenario: StrategyScenario, group: list[CallToArmsState]
) -> CallToArmsState | None:
    joining = [
        (sum(join_score_terms(world, scenario, call).values()), call)
        for call in group
        if npc_answer(world, scenario, call).is_joining
    ]
    if not joining:
        return None
    return sorted(joining, key=lambda item: (-item[0], item[1].id))[0][1]


def _resolve_group(
    world: WorldState, scenario: StrategyScenario, group: list[CallToArmsState]
) -> list[EventLogEntry]:
    war = _find_war(world, group[0].war_id)
    if war is None or side_of(war, group[0].ally_id) is not None:
        for call in group:
            _remove_call(world, call)
        return []
    is_player = world.factions[group[0].ally_id].is_player
    best = None if is_player else _best_joining_call(world, scenario, group)
    ordered = ([best] if best else []) + [item for item in group if item is not best]
    events: list[EventLogEntry] = []
    for call in ordered:
        if _find_call(world, call.id) is not None:
            events += _answer_call(world, scenario, call, call is best)
    return events


def resolve_calls(world: WorldState, scenario: StrategyScenario) -> list[EventLogEntry]:
    due = [
        item for item in world.alliance.calls if item.deadline_turn <= world.clock.turn
    ]
    groups: dict[tuple[str, str], list[CallToArmsState]] = {}
    for call in sorted(due, key=lambda item: item.id):
        groups.setdefault((call.ally_id, call.war_id), []).append(call)
    events: list[EventLogEntry] = []
    for key in sorted(groups):
        events += _resolve_group(world, scenario, groups[key])
    return events
