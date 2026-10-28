from app.engine.diplomacy.events import diplomacy_event
from app.engine.economy.income import faction_income
from app.engine.economy.ledger import available_cash, change_treasury
from app.engine.economy.state import EconomyRun
from app.engine.vassals.registry import is_vassalage_in_force, vassal_term
from app.models.world_diplomacy import CommitmentState
from app.models.world_events import PhaseName
from app.models.world_state import WorldState
from strategy_contracts.limits import FULL_SHARE_PERCENT
from strategy_contracts.terms import VassalTerm

TRIBUTE_PAID = "tribute_paid"


def _active_vassalages(world: WorldState) -> list[CommitmentState]:
    return sorted(
        (item for item in world.commitments if is_vassalage_in_force(world, item)),
        key=lambda item: item.id,
    )


def _is_collectable(world: WorldState, term: VassalTerm) -> bool:
    return not any(
        world.factions[faction_id].is_destroyed
        for faction_id in (term.overlord_id, term.vassal_id)
    )


def collect_vassal_tribute(run: EconomyRun) -> None:
    world = run.world
    if world.vassal_ruleset < 1:
        return
    for commitment in _active_vassalages(world):
        term = vassal_term(commitment)
        if term.tribute_share_percent == 0 or not _is_collectable(world, term):
            continue
        income = faction_income(world, run.tuning, term.vassal_id).total
        vassal = world.factions[term.vassal_id]
        owed = income * term.tribute_share_percent // FULL_SHARE_PERCENT
        amount = min(owed, available_cash(vassal))
        if amount <= 0:
            continue
        changes = [
            change_treasury(vassal, -amount),
            change_treasury(world.factions[term.overlord_id], amount),
        ]
        run.events.append(
            diplomacy_event(
                TRIBUTE_PAID,
                [term.overlord_id, term.vassal_id],
                {"amount": amount},
                phase=PhaseName.ECONOMY,
                changes=changes,
            )
        )
