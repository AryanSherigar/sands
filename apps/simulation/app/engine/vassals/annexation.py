from app.engine.coalitions.ledger import record_conquests
from app.engine.diplomacy.events import diplomacy_event
from app.engine.pressure.wars import side_score, wars_of
from app.engine.vassals.cleanup import clear_vassalage_state
from app.engine.vassals.registry import vassal_term, vassalage_by_id
from app.exceptions.command_exceptions import CommandError
from app.models.orders import AnnexVassalOrder
from app.models.world_diplomacy import CommitmentStatus
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from app.models.world_vassal import AnnexationRecord
from strategy_contracts.ids import FactionId, RegionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import AllianceTerm, NonAggressionTerm, VassalTerm

VASSAL_ANNEXED = "vassal_annexed"
HTTP_UNPROCESSABLE = 422


def _reject(reason: str) -> CommandError:
    return CommandError("order not possible", reason, HTTP_UNPROCESSABLE)


def _best_war_score(world: WorldState, faction_id: FactionId) -> int:
    return max(
        (side_score(war, faction_id) for war in wars_of(world, faction_id)), default=0
    )


def validate_annex_vassal(
    world: WorldState, scenario: StrategyScenario, order: AnnexVassalOrder
) -> None:
    commitment = vassalage_by_id(world, order.vassalage_id)
    if commitment is None:
        raise _reject("unknown_vassalage")
    if vassal_term(commitment).overlord_id != order.faction_id:
        raise _reject("not_overlord")
    tuning = scenario.tuning.vassal
    if _best_war_score(world, order.faction_id) < tuning.annex_min_score:
        raise _reject("score_too_low")
    if world.factions[order.faction_id].stability < tuning.annex_min_stability:
        raise _reject("stability_too_low")
    if any(item.vassalage_id == commitment.id for item in world.vassal.demands):
        raise _reject("demand_pending")


def _transfer_regions(
    world: WorldState, overlord_id: FactionId, vassal_id: FactionId
) -> list[RegionId]:
    taken = sorted(k for k, r in world.regions.items() if r.owner_id == vassal_id)
    for region_id in taken:
        world.regions[region_id].owner_id = overlord_id
    return taken


def _absorb_assets(
    world: WorldState, overlord_id: FactionId, vassal_id: FactionId
) -> None:
    for army in world.armies.values():
        if army.owner_id == vassal_id:
            army.owner_id = overlord_id
    vassal = world.factions[vassal_id]
    world.factions[overlord_id].treasury += max(0, vassal.treasury)
    vassal.treasury = 0


def _leave_wars(world: WorldState, vassal_id: FactionId) -> None:
    for war in wars_of(world, vassal_id):
        if vassal_id in {war.attacker_id, war.defender_id}:
            world.wars = [item for item in world.wars if item.id != war.id]
            world.pressure.stalemate_turns.pop(war.id, None)
            continue
        war.participant_ids = [i for i in war.participant_ids if i != vassal_id]
        war.side_by_faction.pop(vassal_id, None)


def _term_parties(term: object) -> set[FactionId]:
    if isinstance(term, VassalTerm):
        return {term.overlord_id, term.vassal_id}
    if isinstance(term, AllianceTerm | NonAggressionTerm):
        return {term.faction_a, term.faction_b}
    return set()


def _expire_agreements(world: WorldState, vassal_id: FactionId) -> None:
    for commitment in world.commitments:
        is_party = vassal_id in _term_parties(commitment.term)
        if is_party and commitment.status is CommitmentStatus.ACTIVE:
            commitment.status = CommitmentStatus.EXPIRED
            clear_vassalage_state(world, commitment.id)
    world.truces = [
        t for t in world.truces if vassal_id not in {t.faction_a, t.faction_b}
    ]
    world.alliance.calls = [
        c for c in world.alliance.calls if vassal_id not in {c.caller_id, c.ally_id}
    ]


def annex_vassal(
    world: WorldState, scenario: StrategyScenario, order: AnnexVassalOrder
) -> list[EventLogEntry]:
    commitment = vassalage_by_id(world, order.vassalage_id)
    assert commitment is not None
    term = vassal_term(commitment)
    taken = _transfer_regions(world, term.overlord_id, term.vassal_id)
    record_conquests(world, scenario, term.overlord_id, taken)
    wealth = sum(world.regions[region_id].wealth for region_id in taken)
    _absorb_assets(world, term.overlord_id, term.vassal_id)
    _leave_wars(world, term.vassal_id)
    _expire_agreements(world, term.vassal_id)
    commitment.status = CommitmentStatus.FULFILLED
    world.factions[term.vassal_id].is_destroyed = True
    world.vassal.annexations.append(
        AnnexationRecord(
            turn=world.clock.turn,
            overlord_id=term.overlord_id,
            vassal_id=term.vassal_id,
            region_ids=taken,
            wealth=wealth,
        )
    )
    return [
        diplomacy_event(
            VASSAL_ANNEXED,
            [term.overlord_id, term.vassal_id],
            {"regions": len(taken), "wealth": wealth},
            is_major=True,
        )
    ]
