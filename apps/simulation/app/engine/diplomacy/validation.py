from app.engine.alliances.answers import validate_answer_call
from app.engine.alliances.denounce import validate_denounce
from app.engine.diplomacy.grounds import is_usable
from app.engine.diplomacy.prisoners import (
    find_exchange_counterpart,
    find_prisoner,
    ransom_price,
)
from app.engine.peace.hostages import find_hostage
from app.engine.pressure.forcers import has_open_offer
from app.engine.trait_axes import axis_totals
from app.engine.vassals.commands import VassalOrder, validate_vassal_order
from app.engine.vassals.consent import validate_overlord_consent
from app.exceptions.command_exceptions import CommandError
from app.models.orders import (
    AnswerCallOrder,
    CallNegotiationOrder,
    DeclareWarOrder,
    DenounceAllianceOrder,
    DiplomaticPlayOrder,
    FabricateClaimOrder,
    HandlePrisonerOrder,
    MediateOrder,
    SendEnvoyOrder,
)
from app.models.world_diplomacy import PrisonerState
from app.models.world_peace import HostageState
from app.models.world_state import WorldState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.enums import RelationStatus
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import CedeRegionTerm, PayGoldTerm
from strategy_contracts.traits import TraitAxis

DiplomacyOrder = (
    DeclareWarOrder
    | DiplomaticPlayOrder
    | CallNegotiationOrder
    | FabricateClaimOrder
    | SendEnvoyOrder
    | HandlePrisonerOrder
    | MediateOrder
    | AnswerCallOrder
    | DenounceAllianceOrder
    | VassalOrder
)
HTTP_UNPROCESSABLE = 422


def _reject(reason: str) -> CommandError:
    return CommandError("order not possible", reason, HTTP_UNPROCESSABLE)


def is_at_war(world: WorldState, first: str, second: str) -> bool:
    pair = tuple(sorted((first, second)))
    return any(
        (relation.faction_a, relation.faction_b) == pair
        and relation.status == RelationStatus.WAR
        for relation in world.relations
    )


def _require_parties(world: WorldState, command: DiplomacyOrder) -> None:
    if command.target_faction_id == command.faction_id:
        raise _reject("self_target")
    target = world.factions.get(command.target_faction_id)
    if target is None:
        raise _reject("unknown_target")
    if target.is_destroyed:
        raise _reject("target_destroyed")
    if target.leader_id is None or world.factions[command.faction_id].leader_id is None:
        raise _reject("no_leader")
    if is_at_war(world, command.faction_id, command.target_faction_id):
        raise _reject("already_at_war")


def _require_new_envoy(world: WorldState, command: SendEnvoyOrder) -> None:
    if any(
        (envoy.from_faction_id, envoy.at_faction_id)
        == (command.faction_id, command.target_faction_id)
        for envoy in world.envoys
    ):
        raise _reject("envoy_already_there")


def _require_ground(
    world: WorldState, scenario: StrategyScenario, command: DeclareWarOrder
) -> None:
    if command.ground_id is None:
        return
    ground = next(
        (item for item in world.grounds if item.id == command.ground_id), None
    )
    if ground is None or ground.holder_faction_id != command.faction_id:
        raise _reject("unknown_ground")
    if ground.target_faction_id != command.target_faction_id:
        raise _reject("unknown_ground")
    if not is_usable(world, scenario, ground):
        raise _reject("ground_not_usable")


def _require_demand_terms(world: WorldState, command: DiplomaticPlayOrder) -> None:
    if not command.demands:
        raise _reject("bad_demand_term")
    for term in command.demands:
        if not isinstance(term, CedeRegionTerm | PayGoldTerm):
            raise _reject("term_not_supported")
        if not _is_well_formed_demand(world, command, term):
            raise _reject("bad_demand_term")


def _is_well_formed_demand(
    world: WorldState, command: DiplomaticPlayOrder, term: CedeRegionTerm | PayGoldTerm
) -> bool:
    if isinstance(term, PayGoldTerm):
        return (term.payer_id, term.payee_id) == (
            command.target_faction_id,
            command.faction_id,
        )
    region = world.regions.get(term.region_id)
    return (
        region is not None
        and region.owner_id == command.target_faction_id
        and (term.from_faction_id, term.to_faction_id)
        == (command.target_faction_id, command.faction_id)
    )


def _require_forgery(
    world: WorldState, scenario: StrategyScenario, command: FabricateClaimOrder
) -> None:
    region = world.regions.get(command.region_id)
    if region is None or region.owner_id != command.target_faction_id:
        raise _reject("region_unknown")
    leader = world.leaders[world.factions[command.faction_id].leader_id or ""]
    if axis_totals(leader, scenario)[TraitAxis.CUNNING] <= 0:
        raise _reject("not_cunning")
    if any(
        (ground.holder_faction_id, ground.target_faction_id, ground.region_id)
        == (command.faction_id, command.target_faction_id, command.region_id)
        and ground.kind == GroundKind.CLAIM
        for ground in world.grounds
    ):
        raise _reject("already_claimed")


def _require_hostage_action(
    hostage: HostageState, command: HandlePrisonerOrder
) -> None:
    if hostage.holder_id != command.faction_id:
        raise _reject("not_holder")
    if command.action not in ("release", "execute"):
        raise _reject("invalid_hostage_action")


def validate_prisoner_order(
    world: WorldState, scenario: StrategyScenario, command: HandlePrisonerOrder
) -> None:
    if not world.peace_ruleset:
        raise _reject("peace_disabled")
    hostage = find_hostage(world, command.prisoner_id)
    if hostage is not None:
        _require_hostage_action(hostage, command)
        return
    prisoner = find_prisoner(world, command.prisoner_id)
    if prisoner is None:
        raise _reject("unknown_prisoner")
    if prisoner.held_by_id != command.faction_id:
        raise _reject("not_holder")
    if (
        command.action == "exchange"
        and find_exchange_counterpart(world, prisoner) is None
    ):
        raise _reject("no_exchange_counterpart")
    if command.action == "ransom":
        _require_ransom_payer(world, scenario, prisoner)


def _require_ransom_payer(
    world: WorldState, scenario: StrategyScenario, prisoner: PrisonerState
) -> None:
    price = ransom_price(prisoner, scenario.tuning.peace)
    if world.factions[prisoner.origin_faction_id].treasury < price:
        raise _reject("cannot_pay")


def validate_mediate_order(world: WorldState, command: MediateOrder) -> None:
    if not world.peace_ruleset:
        raise _reject("peace_disabled")
    war = next((item for item in world.wars if item.id == command.war_id), None)
    if war is None:
        raise _reject("unknown_war")
    sides = {war.attacker_id, war.defender_id, *war.participant_ids}
    if command.faction_id in sides:
        raise _reject("mediator_is_belligerent")
    mediator = world.factions[command.faction_id]
    if mediator.is_destroyed or mediator.leader_id is None:
        raise _reject("mediator_unavailable")
    if has_open_offer(world, war.id):
        raise _reject("offer_exists")


def _validate_standalone_order(
    world: WorldState, command: DiplomacyOrder, scenario: StrategyScenario
) -> bool:
    if isinstance(command, HandlePrisonerOrder):
        validate_prisoner_order(world, scenario, command)
    elif isinstance(command, MediateOrder):
        validate_mediate_order(world, command)
    elif isinstance(command, AnswerCallOrder):
        validate_answer_call(world, command)
    elif isinstance(command, DenounceAllianceOrder):
        validate_denounce(world, command)
    elif isinstance(command, VassalOrder):
        validate_vassal_order(world, scenario, command)
    else:
        return False
    return True


def validate_diplomacy_order(
    world: WorldState, command: DiplomacyOrder, scenario: StrategyScenario
) -> None:
    if not world.diplomacy_ruleset:
        raise _reject("diplomacy_disabled")
    if _validate_standalone_order(world, command, scenario):
        return
    _require_parties(world, command)
    if isinstance(
        command, DeclareWarOrder | DiplomaticPlayOrder | CallNegotiationOrder
    ):
        validate_overlord_consent(world, command)
    if isinstance(command, SendEnvoyOrder):
        _require_new_envoy(world, command)
        return
    if isinstance(command, DeclareWarOrder):
        _require_ground(world, scenario, command)
        return
    if isinstance(command, FabricateClaimOrder):
        _require_forgery(world, scenario, command)
        return
    if world.factions[command.target_faction_id].is_player:
        raise _reject("target_is_player")
    if isinstance(command, DiplomaticPlayOrder):
        _require_demand_terms(world, command)
