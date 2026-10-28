from app.engine.commands.budget import command_cost
from app.engine.commands.ledger import PENDING_STATUSES
from app.engine.internal.rebel_armies import rebel_army_id
from app.engine.internal.response_previews import preview_response
from app.engine.internal.uprising_lifecycle import is_easing
from app.models.api_world_view import (
    EffectPreview,
    UprisingResponseView,
    UprisingView,
)
from app.models.battle_command import ResolveUprisingCommand
from app.models.world_internal import (
    STAGE_ORDER,
    UprisingResponse,
    UprisingStage,
    UprisingState,
    allowed_responses,
)
from app.models.world_state import UPRISING_LIFECYCLE_RULESET, WorldState
from strategy_contracts.scenario import InternalTuning, StrategyScenario


def project_uprisings(
    world: WorldState, scenario: StrategyScenario, faction_id: str
) -> list[UprisingView]:
    return [
        _uprising_view(world, scenario, uprising)
        for uprising in sorted(world.uprisings, key=lambda item: item.id)
        if uprising.faction_id == faction_id
    ]


def _uprising_view(
    world: WorldState, scenario: StrategyScenario, uprising: UprisingState
) -> UprisingView:
    tuning = scenario.tuning.internal
    queued = _queued_response(world, uprising)
    is_lifecycle = world.internal_ruleset >= UPRISING_LIFECYCLE_RULESET
    return UprisingView(
        **uprising.model_dump(),
        responses=_responses(world, scenario, uprising) if is_lifecycle else [],
        turns_until_change=_turns_until_change(uprising, tuning),
        is_final_stage=uprising.stage is STAGE_ORDER[-1],
        is_easing=is_easing(world, uprising),
        rebel_troops=_rebel_troops(world, uprising),
        queued_response=queued[1] if queued else None,
        queued_command_id=queued[0] if queued else None,
    )


def _rebel_troops(world: WorldState, uprising: UprisingState) -> int | None:
    army = world.armies.get(rebel_army_id(uprising.id))
    return sum(army.troops.values()) if army is not None else None


def _responses(
    world: WorldState, scenario: StrategyScenario, uprising: UprisingState
) -> list[UprisingResponseView]:
    faction = world.factions[uprising.faction_id]
    views: list[UprisingResponseView] = []
    for response in sorted(allowed_responses(uprising), key=lambda item: item.value):
        order = ResolveUprisingCommand(
            faction_id=faction.id, uprising_id=uprising.id, response=response
        )
        cost = command_cost(order, scenario, world)
        preview = preview_response(response, uprising, scenario.tuning.internal)
        views.append(
            UprisingResponseView(
                id=response,
                order_cost=cost,
                effects=[
                    EffectPreview(kind=kind, amount=amount)
                    for kind, amount in preview.effects
                ],
                notes=list(preview.notes),
                is_affordable=faction.orders_remaining >= cost,
            )
        )
    return views


def _turns_until_change(uprising: UprisingState, tuning: InternalTuning) -> int:
    limit = (
        tuning.uprising_armed_flip_turns
        if uprising.stage is UprisingStage.ARMED
        else tuning.uprising_escalate_after_turns
    )
    return max(0, limit - uprising.turns_in_stage)


def _queued_response(
    world: WorldState, uprising: UprisingState
) -> tuple[str, UprisingResponse] | None:
    for accepted in world.accepted_commands:
        command = accepted.command
        is_queued = (
            isinstance(command, ResolveUprisingCommand)
            and command.uprising_id == uprising.id
            and accepted.status in PENDING_STATUSES
        )
        if is_queued:
            return accepted.id, command.response
    return None
