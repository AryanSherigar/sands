from uuid import UUID

from app.engine.alliances.registry import alliance_between
from app.engine.diplomacy.counters import next_counter
from app.engine.diplomacy.events import diplomacy_event
from app.engine.vassals.registry import overlord_of
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_diplomacy import CommitmentState
from app.models.world_events import EventLogEntry
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import TermsCard, VassalTerm

VASSALAGE_SIGNED = "vassalage_signed"
INVALID_TERM = "invalid_term"


def _reject() -> CampaignProgressError:
    return CampaignProgressError("vassal terms are invalid", INVALID_TERM, 422)


def _is_at_war(world: WorldState, term: VassalTerm) -> bool:
    pair = sorted((term.overlord_id, term.vassal_id))
    return any(
        [relation.faction_a, relation.faction_b] == pair
        and relation.status == RelationStatus.WAR
        for relation in world.relations
    )


def _is_cycle(world: WorldState, term: VassalTerm) -> bool:
    current = overlord_of(world, term.overlord_id)
    seen = {term.overlord_id}
    while current is not None and current not in seen:
        if current == term.vassal_id:
            return True
        seen.add(current)
        current = overlord_of(world, current)
    return False


def _validate(world: WorldState, term: VassalTerm) -> None:
    if world.vassal_ruleset < 1 or term.overlord_id == term.vassal_id:
        raise _reject()
    for faction_id in (term.overlord_id, term.vassal_id):
        faction = world.factions.get(faction_id)
        if faction is None or faction.is_destroyed:
            raise _reject()
    if _is_at_war(world, term) or overlord_of(world, term.vassal_id) is not None:
        raise _reject()
    if alliance_between(world, term.overlord_id, term.vassal_id) is not None:
        raise _reject()
    if _is_cycle(world, term):
        raise _reject()


def sign_vassalage(
    world: WorldState,
    scenario: StrategyScenario,
    term: VassalTerm,
    scene_id: UUID | str,
) -> list[EventLogEntry]:
    _validate(world, term)
    end_turn = world.clock.turn + term.duration_turns if term.duration_turns else None
    world.commitments.append(
        CommitmentState(
            id=f"commitment_{next_counter(world, CounterKind.COMMITMENT)}",
            term=term,
            start_turn=world.clock.turn,
            end_turn=end_turn,
            origin_scene_id=UUID(str(scene_id)),
        )
    )
    return [
        diplomacy_event(
            VASSALAGE_SIGNED, [term.overlord_id, term.vassal_id], is_major=True
        )
    ]


def sign_vassal_card(
    world: WorldState,
    scenario: StrategyScenario,
    card: TermsCard,
    scene_id: UUID | str,
) -> list[EventLogEntry]:
    terms = [term for term in card.terms if isinstance(term, VassalTerm)]
    if len(terms) != len(card.terms):
        raise _reject()
    events: list[EventLogEntry] = []
    for term in terms:
        events += sign_vassalage(world, scenario, term, scene_id)
    return events
