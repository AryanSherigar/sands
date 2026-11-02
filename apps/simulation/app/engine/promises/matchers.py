from collections.abc import Callable

from app.engine.alliances.signing import ALLIANCE_SIGNED
from app.engine.diplomacy.prisoners import PRISONER_EXECUTED
from app.engine.diplomacy.war_declaration import WAR_DECLARED
from app.engine.sieges.events import REGION_OCCUPIED
from app.engine.vassals.registry import vassal_term, vassalage_of
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.terms import PromiseKind, SwornPromiseTerm

Matcher = Callable[[SwornPromiseTerm, EventLogEntry], bool]
WAR_ATTACKER_INDEX = 1
WAR_TARGET_INDEX = 2
PRISONER_HOLDER_INDEX = 1
PRISONER_ORIGIN_INDEX = 2
OCCUPIER_INDEX = 0
OCCUPIED_REGION_INDEX = 1


def _subjects(event: EventLogEntry, kind: str, size: int) -> list[str]:
    subject_ids = event.cause.subject_ids
    if event.kind != kind or len(subject_ids) < size:
        return []
    return subject_ids


def _is_attack(term: SwornPromiseTerm, event: EventLogEntry) -> bool:
    subject_ids = _subjects(event, WAR_DECLARED, WAR_TARGET_INDEX + 1)
    if not subject_ids:
        return False
    return (subject_ids[WAR_ATTACKER_INDEX], subject_ids[WAR_TARGET_INDEX]) == (
        term.promisor_id,
        term.beneficiary_id,
    )


def _is_forbidden_alliance(term: SwornPromiseTerm, event: EventLogEntry) -> bool:
    subject_ids = _subjects(event, ALLIANCE_SIGNED, 2)
    if not subject_ids:
        return False
    return set(subject_ids[:2]) == {term.promisor_id, term.subject_id}


def _is_prisoner_executed(term: SwornPromiseTerm, event: EventLogEntry) -> bool:
    subject_ids = _subjects(event, PRISONER_EXECUTED, PRISONER_ORIGIN_INDEX + 1)
    if not subject_ids:
        return False
    return (
        subject_ids[PRISONER_HOLDER_INDEX],
        subject_ids[PRISONER_ORIGIN_INDEX],
    ) == (term.promisor_id, term.beneficiary_id)


def _is_forbidden_occupation(term: SwornPromiseTerm, event: EventLogEntry) -> bool:
    subject_ids = _subjects(event, REGION_OCCUPIED, OCCUPIED_REGION_INDEX + 1)
    if not subject_ids:
        return False
    return (subject_ids[OCCUPIER_INDEX], subject_ids[OCCUPIED_REGION_INDEX]) == (
        term.promisor_id,
        term.subject_id,
    )


MATCHERS: dict[PromiseKind, Matcher] = {
    PromiseKind.NEVER_ATTACK_FACTION: _is_attack,
    PromiseKind.NEVER_ALLY_WITH: _is_forbidden_alliance,
    PromiseKind.SPARE_PRISONERS: _is_prisoner_executed,
    PromiseKind.NEVER_OCCUPY_REGION: _is_forbidden_occupation,
}


def is_breach(term: SwornPromiseTerm, event: EventLogEntry) -> bool:
    return MATCHERS[term.promise](term, event)


def is_proxy_breach(
    world: WorldState, term: SwornPromiseTerm, event: EventLogEntry
) -> bool:
    """A controlled vassal's war breaks its overlord's promise not to attack."""
    if term.promise is not PromiseKind.NEVER_ATTACK_FACTION:
        return False
    subject_ids = _subjects(event, WAR_DECLARED, WAR_TARGET_INDEX + 1)
    if not subject_ids or subject_ids[WAR_TARGET_INDEX] != term.beneficiary_id:
        return False
    commitment = vassalage_of(world, subject_ids[WAR_ATTACKER_INDEX])
    if commitment is None:
        return False
    vassalage = vassal_term(commitment)
    return (
        vassalage.overlord_id == term.promisor_id
        and vassalage.is_foreign_policy_controlled
    )
