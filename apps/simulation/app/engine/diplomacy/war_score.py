from app.engine.battles.state import troop_count
from app.engine.diplomacy.events import diplomacy_event
from app.engine.pressure.wars import side_of
from app.models.world_battle import BattleOutcome, BattleState, BattleStatus
from app.models.world_diplomacy import WarSide, WarState
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_state import WorldState
from strategy_contracts.diplomacy import DiplomacyTuning, ScoreSource
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario

ATTACKER_WINS = frozenset(
    (BattleOutcome.ATTACKER_VICTORY, BattleOutcome.DEFENDER_SURRENDER)
)
DEFENDER_WINS = frozenset(
    (BattleOutcome.DEFENDER_VICTORY, BattleOutcome.ATTACKER_SURRENDER)
)


def goal_slots(side_score: int, tuning: DiplomacyTuning) -> int:
    return 1 + sum(
        1 for threshold in tuning.goal_slot_thresholds if threshold <= side_score
    )


def _winner_and_loser(battle: BattleState) -> tuple[FactionId, FactionId] | None:
    attacker, defender = (
        battle.attacker_lead_faction_id,
        battle.defender_lead_faction_id,
    )
    if attacker is None or defender is None:
        return None
    if battle.outcome in ATTACKER_WINS:
        return attacker, defender
    if battle.outcome in DEFENDER_WINS:
        return defender, attacker
    return None


def _are_opposed_leads(war: WarState, battle: BattleState) -> bool:
    sides = {
        side_of(war, battle.attacker_lead_faction_id),
        side_of(war, battle.defender_lead_faction_id),
    }
    return sides == {WarSide.ATTACKER, WarSide.DEFENDER}


def _is_scorable(war: WarState, battle: BattleState) -> bool:
    return (
        battle.status == BattleStatus.RESOLVED
        and battle.id not in war.scored_battle_ids
        and battle.created_turn >= war.started_turn
        and _are_opposed_leads(war, battle)
    )


def _battle_points(
    world: WorldState, battle: BattleState, loser: FactionId, tuning: DiplomacyTuning
) -> int:
    points = tuning.score_weights[ScoreSource.BATTLE_WON]
    if troop_count(world, battle.contingents[loser]) == 0:
        points += tuning.score_weights[ScoreSource.ARMY_DESTROYED]
    return points


def _score_battles(world: WorldState, war: WarState, tuning: DiplomacyTuning) -> None:
    for battle in sorted(world.battles, key=lambda item: item.id):
        outcome = _winner_and_loser(battle)
        if outcome is None or not _is_scorable(war, battle):
            continue
        winner, loser = outcome
        points = _battle_points(world, battle, loser, tuning)
        if side_of(war, winner) is WarSide.ATTACKER:
            war.battle_points_attacker += points
        else:
            war.battle_points_defender += points
        war.scored_battle_ids.append(battle.id)


def _prisoner_points(
    world: WorldState, holder: FactionId, origin: FactionId, tuning: DiplomacyTuning
) -> int:
    held = sum(
        prisoner.troop_count
        for prisoner in world.prisoners
        if prisoner.held_by_id == holder and prisoner.origin_faction_id == origin
    )
    return (
        held
        // tuning.prisoners_per_score_point
        * tuning.score_weights[ScoreSource.PRISONERS_HELD]
    )


def _totals(
    world: WorldState, war: WarState, tuning: DiplomacyTuning
) -> tuple[int, int]:
    war.prisoner_points_attacker = _prisoner_points(
        world, war.attacker_id, war.defender_id, tuning
    )
    war.prisoner_points_defender = _prisoner_points(
        world, war.defender_id, war.attacker_id, tuning
    )
    cap = tuning.war_score_cap
    chips = (
        world.peace.ransom_points.get(f"{war.id}:{war.attacker_id}", 0),
        world.peace.ransom_points.get(f"{war.id}:{war.defender_id}", 0),
    )
    return (
        min(cap, war.battle_points_attacker + war.prisoner_points_attacker + chips[0]),
        min(cap, war.battle_points_defender + war.prisoner_points_defender + chips[1]),
    )


def tally_war_scores(
    world: WorldState, scenario: StrategyScenario
) -> list[EventLogEntry]:
    tuning = scenario.tuning.diplomacy
    events: list[EventLogEntry] = []
    for war in world.wars:
        before = (war.war_score_attacker, war.war_score_defender)
        _score_battles(world, war, tuning)
        war.war_score_attacker, war.war_score_defender = _totals(world, war, tuning)
        if before != (war.war_score_attacker, war.war_score_defender):
            events.append(
                diplomacy_event(
                    "war_score_changed",
                    [war.id],
                    {
                        "attacker": war.war_score_attacker,
                        "defender": war.war_score_defender,
                    },
                    phase=PhaseName.TIME,
                )
            )
    return events
