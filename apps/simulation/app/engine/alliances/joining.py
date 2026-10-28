from app.engine.alliances.registry import alliance_between, set_pair_relation
from app.engine.diplomacy.events import diplomacy_event
from app.engine.peace.truces import breach_agreements
from app.engine.pressure.wars import opposing_ids
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_alliance import CallToArmsState
from app.models.world_diplomacy import (
    CommitmentStatus,
    WarGoalState,
    WarSide,
    WarState,
)
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario

ALLY_JOINED = "ally_joined"


def _find_war(world: WorldState, war_id: str) -> WarState:
    war = next((item for item in world.wars if item.id == war_id), None)
    if war is None:
        raise CampaignProgressError("the war has ended", "no_war", 422)
    return war


def _seed_side_map(war: WarState) -> None:
    war.side_by_faction.setdefault(war.attacker_id, WarSide.ATTACKER)
    war.side_by_faction.setdefault(war.defender_id, WarSide.DEFENDER)


def _own_goal(war: WarState, call: CallToArmsState) -> list[WarGoalState]:
    if war.ground_kind is None:
        return []
    caller_goal = next(
        (goal for goal in war.goals if goal.faction_id == call.caller_id), None
    )
    region_id = caller_goal.region_id if caller_goal is not None else None
    return [
        WarGoalState(faction_id=call.ally_id, kind=war.ground_kind, region_id=region_id)
    ]


def _end_alliance_quietly(
    world: WorldState, ally_id: FactionId, enemy_id: FactionId
) -> None:
    alliance = alliance_between(world, ally_id, enemy_id)
    if alliance is not None:
        alliance.status = CommitmentStatus.EXPIRED


def join_war(
    world: WorldState, scenario: StrategyScenario, call: CallToArmsState
) -> list[EventLogEntry]:
    war = _find_war(world, call.war_id)
    _seed_side_map(war)
    war.side_by_faction[call.ally_id] = call.side
    war.participant_ids = sorted({*war.participant_ids, call.ally_id})
    war.goals += _own_goal(war, call)
    events: list[EventLogEntry] = []
    for enemy_id in opposing_ids(war, call.ally_id):
        _end_alliance_quietly(world, call.ally_id, enemy_id)
        events += breach_agreements(world, scenario, call.ally_id, enemy_id)
        set_pair_relation(world, call.ally_id, enemy_id, RelationStatus.WAR)
    events.append(diplomacy_event(ALLY_JOINED, [war.id, call.ally_id, call.caller_id]))
    return events
