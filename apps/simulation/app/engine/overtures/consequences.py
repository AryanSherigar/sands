from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.grounds import grant_ground
from app.engine.opinion import shift_opinion
from app.engine.outrage.ledger import raise_outrage
from app.engine.outrage.levels import LADDER, temper_total
from app.engine.peace.restoration import repudiate_treaty
from app.models.world_events import EventLogEntry, Overture
from app.models.world_state import WorldState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.ids import FactionId
from strategy_contracts.overtures import OvertureKind
from strategy_contracts.scenario import StrategyScenario

OVERTURE_DECLINED = "overture_declined"
DECLINED_CAUSE = "declined_overture"
OPINION_FADE_PER_TURN = 1
EXPLICIT_REFUSAL_PENALTY_DIVISOR = 2
GROUND_KINDS = (OvertureKind.PEACE_OFFER, OvertureKind.DEMAND)


def _outrage_steps(scenario: StrategyScenario, temper: int, *, is_ignored: bool) -> int:
    steps = scenario.tuning.overtures.ignore_outrage_levels
    threshold = scenario.tuning.outrage.trait_shift_total
    if temper >= threshold and is_ignored:
        steps += 1
    if temper <= -threshold:
        steps -= 1
    return min(max(steps, 0), len(LADDER) - 1)


def _should_intensify(
    scenario: StrategyScenario, overture: Overture, temper: int, *, is_ignored: bool
) -> bool:
    is_proud = temper >= scenario.tuning.outrage.trait_shift_total
    return is_ignored and is_proud and overture.kind in GROUND_KINDS


def _should_repudiate(
    scenario: StrategyScenario, overture: Overture, temper: int, *, is_ignored: bool
) -> bool:
    is_resentful = temper >= scenario.tuning.outrage.trait_shift_total
    is_renewal = overture.kind is OvertureKind.HEIR_RENEWAL
    return is_renewal and is_ignored and is_resentful and overture.truce_id is not None


def apply_overture_declined(
    world: WorldState,
    scenario: StrategyScenario,
    overture: Overture,
    initiator_id: FactionId,
    player_id: FactionId,
    *,
    is_ignored: bool,
) -> list[EventLogEntry]:
    """Declining costs opinion; a demand also angers the sender, and a proud ruler who is ignored takes a ground."""
    tuning = scenario.tuning.overtures
    penalty = tuning.ignore_opinion_penalty
    if not is_ignored:
        penalty //= EXPLICIT_REFUSAL_PENALTY_DIVISOR
    shift_opinion(
        world, initiator_id, player_id, DECLINED_CAUSE, -penalty, OPINION_FADE_PER_TURN
    )
    leader = world.leaders[world.factions[initiator_id].leader_id or ""]
    temper = temper_total(leader, scenario)
    events = [
        diplomacy_event(
            OVERTURE_DECLINED,
            [initiator_id, player_id],
            {"is_ignored": int(is_ignored)},
        )
    ]
    if overture.kind is OvertureKind.DEMAND:
        steps = _outrage_steps(scenario, temper, is_ignored=is_ignored)
        events += raise_outrage(
            world,
            scenario,
            faction_id=initiator_id,
            offender_id=player_id,
            level=LADDER[steps],
        )
    if _should_repudiate(scenario, overture, temper, is_ignored=is_ignored):
        events += repudiate_treaty(
            world, scenario, overture.truce_id or "", initiator_id
        )
    if _should_intensify(scenario, overture, temper, is_ignored=is_ignored):
        grant_ground(
            world,
            scenario,
            kind=GroundKind.INSULT,
            holder_faction_id=initiator_id,
            target_faction_id=player_id,
            strength=tuning.intensify_ground_strength,
        )
    return events
