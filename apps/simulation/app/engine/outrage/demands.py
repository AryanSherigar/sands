from app.engine.diplomacy.grounds import grant_insult_ground
from app.engine.outrage.ledger import raise_outrage
from app.engine.outrage.levels import (
    LADDER,
    demand_price_percent,
    outrage_level,
    temper_total,
)
from app.engine.peace.pricing import price_card
from app.engine.pressure.wars import find_war, side_score
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import OutrageLevel
from strategy_contracts.terms import TermsCard


def _demander_score(
    world: WorldState, demander_id: FactionId, target_id: FactionId
) -> int:
    war = find_war(world, demander_id, target_id)
    return 0 if war is None else side_score(war, demander_id)


def _level_for(
    world: WorldState,
    scenario: StrategyScenario,
    demander_id: FactionId,
    target_id: FactionId,
    card: TermsCard,
    tone_grade: int | None,
) -> OutrageLevel:
    tuning = scenario.tuning.outrage
    demand = price_card(scenario, card, demander_id).demand
    if demand == 0:
        return OutrageLevel.NONE
    percent = demand_price_percent(
        demand=demand,
        demander_score=_demander_score(world, demander_id, target_id),
        tuning=tuning,
    )
    leader = world.leaders[world.factions[target_id].leader_id or ""]
    return outrage_level(percent, temper_total(leader, scenario), tone_grade, tuning)


def _record_tone(world: WorldState, tone_grade: int | None) -> None:
    if tone_grade is None:
        return
    world.player_profile.tone_grade_total += tone_grade
    world.player_profile.tone_grade_count += 1


def react_to_demand(
    world: WorldState,
    scenario: StrategyScenario,
    *,
    demander_id: FactionId,
    card: TermsCard,
    tone_grade: int | None,
) -> list[EventLogEntry]:
    """An overreaching demand angers an NPC target; against the player it only earns them an insult ground."""
    if world.outrage_ruleset < 1 or not scenario.toggles.is_outrage_enabled:
        return []
    target_id = card.counterpart_id
    if world.factions[demander_id].is_player:
        _record_tone(world, tone_grade)
    level = _level_for(world, scenario, demander_id, target_id, card, tone_grade)
    if level == OutrageLevel.NONE:
        return []
    if world.factions[target_id].is_player:
        grant_insult_ground(
            world,
            scenario,
            holder_faction_id=target_id,
            target_faction_id=demander_id,
            grade=LADDER.index(level),
        )
        return []
    return raise_outrage(
        world, scenario, faction_id=target_id, offender_id=demander_id, level=level
    )
