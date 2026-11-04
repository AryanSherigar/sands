from app.engine.diplomacy.collapse_settlement import collapse_cession
from app.engine.diplomacy.events import diplomacy_event
from app.engine.peace.bare_peace import build_bare_peace_card
from app.engine.peace.pricing import can_afford
from app.engine.peace.signing import sign_peace
from app.engine.pressure.wars import side_of
from app.models.world_diplomacy import WarState
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import TermsCard

DECISIVE_DEFEAT = "decisive_defeat"
PERCENT_BASE = 100


def _loser_of(war: WarState) -> FactionId | None:
    if war.war_score_attacker == war.war_score_defender:
        return None
    if war.war_score_attacker > war.war_score_defender:
        return war.defender_id
    return war.attacker_id


def _entry_troops(world: WorldState, war: WarState, faction_id: FactionId) -> int:
    battles = [item for item in world.battles if item.id in war.scored_battle_ids]
    entries = [
        battle.contingents[faction_id].entry_troops
        for battle in battles
        if faction_id in battle.contingents
    ]
    return max(entries, default=0)


def _field_troops(world: WorldState, faction_id: FactionId) -> int:
    return sum(
        sum(army.troops.values())
        for army in world.armies.values()
        if army.owner_id == faction_id
    )


def find_decisively_beaten(
    world: WorldState, scenario: StrategyScenario, war: WarState
) -> FactionId | None:
    """The loser when the enemy's score lead is decisive and the loser's host is broken."""
    loser_id = _loser_of(war)
    if loser_id is None or side_of(war, loser_id) is None:
        return None
    tuning = scenario.tuning.peace
    lead = abs(war.war_score_attacker - war.war_score_defender)
    if lead < tuning.decisive_defeat_score_lead:
        return None
    baseline = _entry_troops(world, war, loser_id)
    if baseline == 0:
        return None
    is_broken = (
        _field_troops(world, loser_id) * PERCENT_BASE
        <= baseline * tuning.decisive_defeat_troop_percent
    )
    return loser_id if is_broken else None


def _forced_peace_card(
    world: WorldState, scenario: StrategyScenario, war: WarState, loser_id: FactionId
) -> TermsCard:
    winner_id = war.defender_id if loser_id == war.attacker_id else war.attacker_id
    card = build_bare_peace_card(war, loser_id, winner_id, [], is_white_peace=False)
    cession = collapse_cession(world, scenario, war, loser_id, winner_id)
    if cession is None:
        return card
    return card.model_copy(update={"terms": [*card.terms, cession]})


def apply_decisive_defeats(
    world: WorldState, scenario: StrategyScenario
) -> list[EventLogEntry]:
    """Ends each war whose loser is decisively beaten with a forced peace and one ceded region.

    NOTE: the defeated side is bound by a short truce, so the war cannot reopen at once.
    """
    if not world.defeat_ruleset:
        return []
    events: list[EventLogEntry] = []
    for war in list(world.wars):
        loser_id = find_decisively_beaten(world, scenario, war)
        if loser_id is None:
            continue
        card = _forced_peace_card(world, scenario, war, loser_id)
        if not can_afford(world, scenario, card, loser_id, war):
            continue
        events += sign_peace(world, scenario, card, f"defeat-{war.id}")
        events.append(
            diplomacy_event(
                DECISIVE_DEFEAT,
                [loser_id, card.counterpart_id, war.id],
                is_major=True,
            )
        )
    return events
