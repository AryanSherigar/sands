from app.engine.vassals.annexation import annex_vassal, validate_annex_vassal
from app.engine.vassals.consent import (
    consent_action_for,
    consume_consent,
    grant_consent,
    validate_grant_consent,
)
from app.engine.vassals.demands import (
    apply_answer_demand,
    issue_demand,
    validate_answer_demand,
    validate_demand_from_vassal,
)
from app.engine.vassals.release import release_vassal, validate_release_vassal
from app.models.orders import (
    AnnexVassalOrder,
    AnswerDemandOrder,
    CallNegotiationOrder,
    DeclareWarOrder,
    DemandFromVassalOrder,
    DiplomaticPlayOrder,
    GrantConsentOrder,
    ReleaseVassalOrder,
)
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario

VassalOrder = (
    GrantConsentOrder
    | DemandFromVassalOrder
    | AnswerDemandOrder
    | ReleaseVassalOrder
    | AnnexVassalOrder
)
VASSAL_REFUNDED_REASONS = frozenset(
    (
        "no_overlord_consent",
        "unknown_vassalage",
        "not_overlord",
        "unknown_target",
        "unknown_demand",
        "not_vassal",
        "demand_expired",
        "demand_pending",
        "demand_cooldown",
        "no_excess",
        "bad_amount",
        "score_too_low",
        "stability_too_low",
    )
)


def consume_used_consent(world: WorldState, order: object) -> None:
    if isinstance(order, DeclareWarOrder | DiplomaticPlayOrder | CallNegotiationOrder):
        consume_consent(
            world, order.faction_id, consent_action_for(order), order.target_faction_id
        )


def validate_vassal_order(
    world: WorldState, scenario: StrategyScenario, order: VassalOrder
) -> None:
    if isinstance(order, GrantConsentOrder):
        validate_grant_consent(world, order)
    elif isinstance(order, DemandFromVassalOrder):
        validate_demand_from_vassal(world, scenario, order)
    elif isinstance(order, ReleaseVassalOrder):
        validate_release_vassal(world, order)
    elif isinstance(order, AnnexVassalOrder):
        validate_annex_vassal(world, scenario, order)
    else:
        validate_answer_demand(world, order)


def apply_vassal_order(
    world: WorldState, scenario: StrategyScenario, order: VassalOrder
) -> list[EventLogEntry]:
    if isinstance(order, GrantConsentOrder):
        return grant_consent(world, scenario, order)
    if isinstance(order, DemandFromVassalOrder):
        return issue_demand(world, scenario, order)
    if isinstance(order, ReleaseVassalOrder):
        return release_vassal(world, order)
    if isinstance(order, AnnexVassalOrder):
        return annex_vassal(world, scenario, order)
    return apply_answer_demand(world, scenario, order)
