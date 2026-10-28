from uuid import UUID

from app.engine.alliances.registry import alliance_between, set_pair_relation
from app.engine.diplomacy.counters import next_counter
from app.engine.diplomacy.events import diplomacy_event
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_diplomacy import CommitmentState
from app.models.world_events import EventLogEntry
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import AllianceTerm, TermsCard

ALLIANCE_SIGNED = "alliance_signed"
INVALID_TERM = "invalid_term"


def _reject() -> CampaignProgressError:
    return CampaignProgressError("alliance terms are invalid", INVALID_TERM, 422)


def _is_at_war(world: WorldState, term: AllianceTerm) -> bool:
    pair = sorted((term.faction_a, term.faction_b))
    return any(
        [relation.faction_a, relation.faction_b] == pair
        and relation.status == RelationStatus.WAR
        for relation in world.relations
    )


def _validate(world: WorldState, term: AllianceTerm) -> None:
    if world.alliance_ruleset < 1 or term.faction_a == term.faction_b:
        raise _reject()
    for faction_id in (term.faction_a, term.faction_b):
        faction = world.factions.get(faction_id)
        if faction is None or faction.is_destroyed:
            raise _reject()
    if _is_at_war(world, term):
        raise _reject()
    if alliance_between(world, term.faction_a, term.faction_b) is not None:
        raise _reject()


def sign_alliance(
    world: WorldState,
    scenario: StrategyScenario,
    term: AllianceTerm,
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
    set_pair_relation(world, term.faction_a, term.faction_b, RelationStatus.ALLIANCE)
    return [
        diplomacy_event(
            ALLIANCE_SIGNED, [term.faction_a, term.faction_b], is_major=True
        )
    ]


def sign_alliance_card(
    world: WorldState,
    scenario: StrategyScenario,
    card: TermsCard,
    scene_id: UUID | str,
) -> list[EventLogEntry]:
    terms = [term for term in card.terms if isinstance(term, AllianceTerm)]
    if len(terms) != len(card.terms):
        raise _reject()
    events: list[EventLogEntry] = []
    for term in terms:
        events += sign_alliance(world, scenario, term, scene_id)
    return events
