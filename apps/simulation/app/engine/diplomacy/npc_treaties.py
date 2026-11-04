from uuid import NAMESPACE_OID, uuid5

from app.engine.ai.situation import war_enemies
from app.engine.treaty.signing import apply_card
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_diplomacy import DiplomaticPlayState
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.diplomacy import DiplomacyTuning
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import (
    AllianceTerm,
    NonAggressionTerm,
    Term,
    TermsCard,
    TradeDealTerm,
)


def _shares_an_enemy(world: WorldState, play: DiplomaticPlayState) -> bool:
    return bool(
        set(war_enemies(world, play.attacker_id))
        & set(war_enemies(world, play.defender_id))
    )


def _terms_for(
    world: WorldState,
    tuning: DiplomacyTuning,
    play: DiplomaticPlayState,
    warmth: int,
) -> list[Term]:
    if warmth < tuning.npc_treaty_warmth:
        return []
    first, second = play.attacker_id, play.defender_id
    if warmth >= tuning.npc_alliance_warmth and _shares_an_enemy(world, play):
        return [
            AllianceTerm(
                faction_a=first,
                faction_b=second,
                duration_turns=tuning.npc_alliance_turns,
            )
        ]
    turns = tuning.npc_treaty_turns
    return [
        NonAggressionTerm(faction_a=first, faction_b=second, duration_turns=turns),
        TradeDealTerm(faction_a=first, faction_b=second, duration_turns=turns),
    ]


def sign_talks_treaty(
    world: WorldState,
    scenario: StrategyScenario,
    play: DiplomaticPlayState,
    warmth: int,
) -> list[EventLogEntry]:
    """Turn warm, accepted NPC talks into a signed card; a card that cannot sign leaves the world untouched."""
    terms = _terms_for(world, scenario.tuning.diplomacy, play, warmth)
    if not terms or world.treaty_ruleset < 1:
        return []
    card = TermsCard(
        proposer_id=play.attacker_id, counterpart_id=play.defender_id, terms=terms
    )
    try:
        return apply_card(world, scenario, card, uuid5(NAMESPACE_OID, play.id))
    except CampaignProgressError:
        return []
