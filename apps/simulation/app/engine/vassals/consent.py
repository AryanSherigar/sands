from app.engine.ai.standing import is_bound
from app.engine.alliances.registry import allies_of
from app.engine.diplomacy.events import diplomacy_event
from app.engine.vassals.registry import (
    vassal_term,
    vassalage_by_id,
    vassalage_of,
)
from app.exceptions.command_exceptions import CommandError
from app.models.orders import (
    CallNegotiationOrder,
    DeclareWarOrder,
    DiplomaticPlayOrder,
    GrantConsentOrder,
)
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from app.models.world_vassal import ConsentState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.vassal import ConsentAction

CONSENT_GRANTED = "consent_granted"
NO_CONSENT = "no_overlord_consent"
HTTP_UNPROCESSABLE = 422

GatedOrder = DeclareWarOrder | DiplomaticPlayOrder | CallNegotiationOrder


def _reject(reason: str) -> CommandError:
    return CommandError("order not possible", reason, HTTP_UNPROCESSABLE)


def _has_grant(
    world: WorldState,
    vassalage_id: str,
    action: ConsentAction,
    target_faction_id: FactionId,
) -> bool:
    return any(
        (item.vassalage_id, item.action, item.target_faction_id)
        == (vassalage_id, action, target_faction_id)
        and item.expires_turn > world.clock.turn
        for item in world.vassal.consents
    )


def _npc_overlord_allows(
    world: WorldState, overlord_id: FactionId, target_faction_id: FactionId
) -> bool:
    if target_faction_id in allies_of(world, overlord_id):
        return False
    return not is_bound(world, overlord_id, target_faction_id)


def has_overlord_consent(
    world: WorldState,
    faction_id: FactionId,
    action: ConsentAction,
    target_faction_id: FactionId,
) -> bool:
    commitment = vassalage_of(world, faction_id)
    if commitment is None or not vassal_term(commitment).is_foreign_policy_controlled:
        return True
    overlord_id = vassal_term(commitment).overlord_id
    if target_faction_id == overlord_id:
        return True
    if world.factions[overlord_id].is_player:
        return _has_grant(world, commitment.id, action, target_faction_id)
    return _npc_overlord_allows(world, overlord_id, target_faction_id)


def consent_action_for(order: GatedOrder) -> ConsentAction:
    if isinstance(order, DeclareWarOrder):
        return ConsentAction.DECLARE_WAR
    if isinstance(order, DiplomaticPlayOrder):
        return ConsentAction.DEMAND
    return ConsentAction.PACT


def validate_overlord_consent(world: WorldState, order: GatedOrder) -> None:
    if world.vassal_ruleset < 1:
        return
    action = consent_action_for(order)
    if not has_overlord_consent(
        world, order.faction_id, action, order.target_faction_id
    ):
        raise _reject(NO_CONSENT)


def validate_grant_consent(world: WorldState, order: GrantConsentOrder) -> None:
    commitment = vassalage_by_id(world, order.vassalage_id)
    if commitment is None:
        raise _reject("unknown_vassalage")
    term = vassal_term(commitment)
    if term.overlord_id != order.faction_id:
        raise _reject("not_overlord")
    if order.target_faction_id not in world.factions:
        raise _reject("unknown_target")


def grant_consent(
    world: WorldState, scenario: StrategyScenario, order: GrantConsentOrder
) -> list[EventLogEntry]:
    world.vassal.consents = [
        item
        for item in world.vassal.consents
        if (item.vassalage_id, item.action, item.target_faction_id)
        != (order.vassalage_id, order.action, order.target_faction_id)
    ]
    world.vassal.consents.append(
        ConsentState(
            vassalage_id=order.vassalage_id,
            action=order.action,
            target_faction_id=order.target_faction_id,
            expires_turn=world.clock.turn + scenario.tuning.vassal.consent_valid_turns,
        )
    )
    return [
        diplomacy_event(CONSENT_GRANTED, [order.faction_id, order.target_faction_id])
    ]


def consume_consent(
    world: WorldState,
    faction_id: FactionId,
    action: ConsentAction,
    target_faction_id: FactionId,
) -> None:
    commitment = vassalage_of(world, faction_id)
    if commitment is None:
        return
    world.vassal.consents = [
        item
        for item in world.vassal.consents
        if (item.vassalage_id, item.action, item.target_faction_id)
        != (commitment.id, action, target_faction_id)
    ]


def expire_consents(world: WorldState) -> None:
    world.vassal.consents = [
        item for item in world.vassal.consents if item.expires_turn > world.clock.turn
    ]
