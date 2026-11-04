from app.engine.proclamations.constants import (
    DEFAULT_PROCLAMATION_DURATION_TURNS,
    RESCIND_UNREST_PENALTY,
)
from app.engine.proclamations.effects import calculate_proclamation_deltas
from app.models.world_state import WorldState
from strategy_contracts.proclamation import (
    ActiveProclamation,
    ProclamationBurden,
    ProclamationDraft,
)


def _apply_unrest_delta(world: WorldState, player_id: str, delta: int) -> None:
    for region in world.regions.values():
        if region.owner_id == player_id:
            region.unrest = min(100, max(0, region.unrest + delta))


def _apply_manpower_delta(world: WorldState, player_id: str, delta: int) -> None:
    # TRADE-OFF: levies may push a region above its refill cap; refill then pauses.
    regions = sorted(
        (
            region
            for region in world.regions.values()
            if region.owner_id == player_id and region.occupation is None
        ),
        key=lambda region: region.id,
    )
    if not regions or not delta:
        return
    sign = -1 if delta < 0 else 1
    base, remainder = divmod(abs(delta), len(regions))
    for index, region in enumerate(regions):
        share = base + (1 if index < remainder else 0)
        region.manpower = max(0, region.manpower + sign * share)


def _apply_morale_delta(world: WorldState, player_id: str, delta: int) -> None:
    for army in world.armies.values():
        if army.owner_id == player_id:
            army.morale = min(100, max(0, army.morale + delta))


def _apply_immediate_deltas(
    world: WorldState, player_id: str, immediate: dict[str, int]
) -> None:
    faction = world.factions.get(player_id)
    if faction is not None and "gold" in immediate:
        faction.treasury = max(0, faction.treasury + immediate["gold"])
    if "unrest" in immediate:
        _apply_unrest_delta(world, player_id, immediate["unrest"])
    if "manpower" in immediate:
        _apply_manpower_delta(world, player_id, immediate["manpower"])
    if "morale" in immediate:
        _apply_morale_delta(world, player_id, immediate["morale"])


def _downgrade_burden(burden: ProclamationBurden) -> ProclamationBurden:
    if burden == ProclamationBurden.RADICAL:
        return ProclamationBurden.SEVERE
    if burden == ProclamationBurden.SEVERE:
        return ProclamationBurden.MODERATE
    return ProclamationBurden.LIGHT


def apply_proclamation_enactment(
    world: WorldState,
    draft: ProclamationDraft,
    is_rescinding: bool = False,
    is_compromise: bool = False,
) -> ActiveProclamation:
    player_id = next((k for k, f in world.factions.items() if f.is_player), "")
    if is_rescinding and world.active_proclamation is not None:
        _apply_unrest_delta(world, player_id, RESCIND_UNREST_PENALTY)

    burden = _downgrade_burden(draft.burden) if is_compromise else draft.burden
    immediate, ongoing = calculate_proclamation_deltas(draft.domain, burden)
    _apply_immediate_deltas(world, player_id, immediate)

    active = ActiveProclamation(
        id=f"proc_{world.clock.turn}_{draft.domain.value}",
        legal_summary=draft.legal_summary,
        domain=draft.domain,
        burden=burden,
        enacted_turn=world.clock.turn,
        remaining_turns=DEFAULT_PROCLAMATION_DURATION_TURNS,
        immediate_deltas=immediate,
        ongoing_modifiers=ongoing,
    )
    world.active_proclamation = active
    return active


def tick_active_proclamation_turn(world: WorldState) -> None:
    if world.active_proclamation is None:
        return
    world.active_proclamation.remaining_turns -= 1
    if world.active_proclamation.remaining_turns <= 0:
        world.active_proclamation = None
