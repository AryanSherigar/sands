from app.engine.pressure.wars import wars_of
from app.models.world_diplomacy import PrisonerKind
from app.models.world_pressure import ShockRecord
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.pressure import ShockKind
from strategy_contracts.scenario import StrategyScenario


def record_shock(
    world: WorldState,
    scenario: StrategyScenario,
    kind: ShockKind,
    faction_id: FactionId,
    war_id: str,
) -> bool:
    if not world.pressure_ruleset:
        return False
    if _find(world, kind, faction_id, war_id) is not None:
        return False
    world.pressure.shocks.append(
        ShockRecord(
            war_id=war_id, faction_id=faction_id, kind=kind, turn=world.clock.turn
        )
    )
    return True


def _find(
    world: WorldState, kind: ShockKind, faction_id: FactionId, war_id: str
) -> ShockRecord | None:
    return next(
        (
            shock
            for shock in world.pressure.shocks
            if (shock.kind, shock.faction_id, shock.war_id)
            == (kind, faction_id, war_id)
        ),
        None,
    )


def _active_shocks(world: WorldState, faction_id: FactionId) -> list[ShockRecord]:
    active_war_ids = {war.id for war in world.wars}
    return [
        shock
        for shock in world.pressure.shocks
        if shock.faction_id == faction_id and shock.war_id in active_war_ids
    ]


def shock_total(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    amounts = scenario.tuning.pressure.shock_amounts
    return sum(amounts[shock.kind] for shock in _active_shocks(world, faction_id))


def _is_capital_lost(world: WorldState, faction_id: FactionId) -> bool:
    capital_id = world.factions[faction_id].capital_region_id
    capital = world.regions.get(capital_id) if capital_id else None
    if capital is None:
        return False
    is_occupied = capital.occupation and capital.occupation.occupier_id != faction_id
    return bool(is_occupied) or capital.owner_id not in (None, faction_id)


def _is_ruler_lost(world: WorldState, faction_id: FactionId) -> bool:
    leader_id = world.factions[faction_id].leader_id
    leader = world.leaders.get(leader_id) if leader_id else None
    if leader is None:
        return False
    is_held = any(
        prisoner.kind is PrisonerKind.CHARACTER and prisoner.character_id == leader.id
        for prisoner in world.prisoners
    )
    return is_held or not leader.is_alive


def _is_home_army_destroyed(world: WorldState, faction_id: FactionId) -> bool:
    return not any(
        sum(army.troops.values())
        for army in world.armies.values()
        if army.owner_id == faction_id
    )


STATE_CHECKS = (
    (ShockKind.CAPITAL_FALLS, _is_capital_lost),
    (ShockKind.RULER_CAPTURED, _is_ruler_lost),
    (ShockKind.HOME_ARMY_DESTROYED, _is_home_army_destroyed),
)


def detect_state_shocks(
    world: WorldState, scenario: StrategyScenario
) -> list[ShockRecord]:
    recorded: list[ShockRecord] = []
    for faction_id, faction in sorted(world.factions.items()):
        wars = wars_of(world, faction_id)
        if not wars or faction.is_destroyed:
            continue
        held = {shock.kind for shock in _active_shocks(world, faction_id)}
        for kind, is_triggered in STATE_CHECKS:
            if kind not in held and is_triggered(world, faction_id):
                record_shock(world, scenario, kind, faction_id, wars[0].id)
                recorded.append(world.pressure.shocks[-1])
    return recorded
