from app.engine.battles.deployment import (
    allocate_largest_remainder,
    reconcile_deployments,
)
from app.engine.battles.state import FIGHTING_STATUSES
from app.engine.economy.armies import remove_army
from app.engine.economy.budget import next_turn_orders
from app.engine.logistics.supply import supply_assessments
from app.engine.movement.costs import months_of_turn
from app.engine.movement.map_index import build_map_index
from app.engine.outrage.effects import mobilization_orders_bonus
from app.engine.visibility.observations import record_visible_observations
from app.models.world_army import ArmyState
from app.models.world_battle import BattleStatus
from app.models.world_character import CommanderStatus
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from app.models.world_events import EventCause, EventLogEntry, PhaseName, StateChange
from app.models.world_state import WorldState
from strategy_contracts.battle import SupplyState
from strategy_contracts.enums import RelationStatus, TroopType
from strategy_contracts.scenario import StrategyScenario

FATIGUE_RECOVERED = "army_fatigue_recovered"
SUPPLY_ATTRITION = "army_supply_attrition"
SUPPLY_WITHDRAWAL = "army_supply_withdrawal"
SUPPLY_SURRENDER = "army_supply_surrender"
SUPPLY_DISBAND = "army_supply_disband"


def _engaged_army_ids(world: WorldState) -> set[str]:
    return {
        army_id
        for battle in world.battles
        if battle.status != BattleStatus.RESOLVED
        for contingent in battle.contingents.values()
        if contingent.status in FIGHTING_STATUSES
        for army_id in contingent.army_ids
    }


def _recovery_event(army_id: str, before: int, after: int) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=PhaseName.TIME,
        kind=FATIGUE_RECOVERED,
        cause=EventCause(
            summary_key=FATIGUE_RECOVERED,
            subject_ids=[army_id],
            inputs={"recovery": before - after},
        ),
        changes=[
            StateChange(path=f"armies.{army_id}.fatigue", before=before, after=after)
        ],
    )


def _supply_event(
    kind: str, army_id: str, inputs: dict[str, int], changes: list[StateChange]
) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=PhaseName.TIME,
        kind=kind,
        cause=EventCause(summary_key=kind, subject_ids=[army_id], inputs=inputs),
        changes=changes,
    )


def _attrition_percent(
    state: SupplyState, winter: bool, scenario: StrategyScenario
) -> int:
    tuning = scenario.tuning.logistics
    base = {
        SupplyState.SUPPLIED: 0,
        SupplyState.STRAINED: tuning.strained_attrition_percent,
        SupplyState.ISOLATED: tuning.isolated_attrition_percent,
    }[state]
    return base + (tuning.winter_attrition_percent if winter else 0)


def _apply_losses(army: ArmyState, percent: int) -> dict[TroopType, int]:
    troops = sum(army.troops.values())
    losses = min(troops, (troops * percent + 99) // 100)
    by_type = allocate_largest_remainder(losses, army.troops)
    for troop_type, loss in by_type.items():
        army.troops[troop_type] -= loss
    return {troop_type: loss for troop_type, loss in by_type.items() if loss}


def _is_friendly(world: WorldState, faction_id: str, owner_id: str | None) -> bool:
    return owner_id == faction_id or any(
        {relation.faction_a, relation.faction_b} == {faction_id, owner_id}
        and relation.status == RelationStatus.ALLIANCE
        for relation in world.relations
    )


def _is_hostile(world: WorldState, faction_id: str, owner_id: str) -> bool:
    return any(
        {relation.faction_a, relation.faction_b} == {faction_id, owner_id}
        and relation.status == RelationStatus.WAR
        for relation in world.relations
    )


def _withdrawal_destination(
    world: WorldState, army_id: str, scenario: StrategyScenario
) -> str | None:
    army = world.armies[army_id]
    index = build_map_index(scenario.map)
    candidates = [
        region_id
        for region_id in index.neighbors.get(army.location_id, frozenset())
        if (region := world.regions.get(region_id)) is not None
        and region.occupation is None
        and _is_friendly(world, army.owner_id, region.owner_id)
    ]
    return min(candidates, default=None)


def _enemy_present(world: WorldState, army_id: str) -> str | None:
    army = world.armies[army_id]
    return next(
        (
            candidate.owner_id
            for _, candidate in sorted(world.armies.items())
            if candidate.location_id == army.location_id
            and _is_hostile(world, army.owner_id, candidate.owner_id)
        ),
        None,
    )


def _surrender_army(world: WorldState, army_id: str, captor_id: str) -> None:
    army = world.armies[army_id]
    troops = {kind: count for kind, count in army.troops.items() if count}
    origin = f"supply:{army.id}:{world.clock.turn}"
    if troops:
        world.prisoners.append(
            PrisonerState(
                id=f"{origin}:troops",
                held_by_id=captor_id,
                origin_faction_id=army.owner_id,
                kind=PrisonerKind.TROOPS,
                troop_count=sum(troops.values()),
                origin_battle_id=origin,
                troops_by_type=troops,
            )
        )
    commander = world.commanders.get(army.commander_id or "")
    if commander is not None:
        commander.status = CommanderStatus.CAPTURED
        commander.army_id = None
        world.prisoners.append(
            PrisonerState(
                id=f"{origin}:commander:{commander.id}",
                held_by_id=captor_id,
                origin_faction_id=army.owner_id,
                kind=PrisonerKind.CHARACTER,
                character_id=commander.id,
            )
        )
    remove_army(world, army_id)


def _resolve_supply_failure(
    world: WorldState, army_id: str, scenario: StrategyScenario
) -> EventLogEntry:
    army = world.armies[army_id]
    destination = _withdrawal_destination(world, army_id, scenario)
    if destination is not None:
        before = army.location_id
        army.location_id = destination
        army.march = None
        return _supply_event(
            SUPPLY_WITHDRAWAL,
            army_id,
            {
                "isolated_turns": scenario.tuning.logistics.forced_withdrawal_after_isolated_turns
            },
            [
                StateChange(
                    path=f"armies.{army_id}.location_id",
                    before=before,
                    after=destination,
                )
            ],
        )
    captor = _enemy_present(world, army_id)
    if captor is not None:
        _surrender_army(world, army_id, captor)
        return _supply_event(
            SUPPLY_SURRENDER,
            army_id,
            {
                "isolated_turns": scenario.tuning.logistics.forced_withdrawal_after_isolated_turns
            },
            [
                StateChange(
                    path=f"armies.{army_id}", before="active", after="surrendered"
                )
            ],
        )
    remove_army(world, army_id)
    return _supply_event(
        SUPPLY_DISBAND,
        army_id,
        {
            "isolated_turns": scenario.tuning.logistics.forced_withdrawal_after_isolated_turns
        },
        [StateChange(path=f"armies.{army_id}", before="active", after="disbanded")],
    )


def _apply_campaign_attrition(
    world: WorldState, scenario: StrategyScenario, engaged: set[str]
) -> list[EventLogEntry]:
    if not world.logistics_ruleset:
        return []
    assessments = supply_assessments(world, scenario)
    winter = any(
        month in scenario.tuning.movement.winter_months
        for month in months_of_turn(world.clock)
    )
    events: list[EventLogEntry] = []
    for army_id in sorted(tuple(world.armies)):
        army = world.armies[army_id]
        if not sum(army.troops.values()):
            continue
        assessment = assessments[(army.owner_id, army.location_id)]
        percent = _attrition_percent(assessment.state, winter, scenario)
        before_troops, before_morale = sum(army.troops.values()), army.morale
        losses = _apply_losses(army, percent) if percent else {}
        morale_loss = (
            scenario.tuning.logistics.isolated_morale_loss
            if assessment.state == SupplyState.ISOLATED
            else scenario.tuning.logistics.strained_morale_loss
            if assessment.state == SupplyState.STRAINED
            else 0
        )
        army.morale = max(0, army.morale - morale_loss)
        if losses or before_morale != army.morale:
            events.append(
                _supply_event(
                    SUPPLY_ATTRITION,
                    army_id,
                    {
                        "isolated": scenario.tuning.logistics.isolated_attrition_percent
                        if assessment.state == SupplyState.ISOLATED
                        else 0,
                        "winter": scenario.tuning.logistics.winter_attrition_percent
                        if winter
                        else 0,
                    },
                    [
                        StateChange(
                            path=f"armies.{army_id}.troops",
                            before=before_troops,
                            after=sum(army.troops.values()),
                        ),
                        StateChange(
                            path=f"armies.{army_id}.morale",
                            before=before_morale,
                            after=army.morale,
                        ),
                    ],
                )
            )
        if assessment.state != SupplyState.ISOLATED:
            world.supply_failure_turns.pop(army_id, None)
            continue
        world.supply_failure_turns[army_id] = (
            world.supply_failure_turns.get(army_id, 0) + 1
        )
        if (
            army_id not in engaged
            and world.supply_failure_turns[army_id]
            >= scenario.tuning.logistics.forced_withdrawal_after_isolated_turns
        ):
            events.append(_resolve_supply_failure(world, army_id, scenario))
            world.supply_failure_turns.pop(army_id, None)
    _reconcile_active_battles(world, scenario)
    return events


def _reconcile_active_battles(world: WorldState, scenario: StrategyScenario) -> None:
    for battle in world.battles:
        if battle.status != BattleStatus.RESOLVED:
            reconcile_deployments(world, battle, scenario.tuning.battle)


def complete_campaign(
    world: WorldState, scenario: StrategyScenario
) -> list[EventLogEntry]:
    engaged = _engaged_army_ids(world)
    for faction_id, faction in world.factions.items():
        faction.orders_remaining = next_turn_orders(
            scenario.tuning.orders_per_turn,
            faction,
            mobilization_orders_bonus(world, scenario, faction_id),
        )
        faction.orders_debt = 0
    events: list[EventLogEntry] = []
    events.extend(_apply_campaign_attrition(world, scenario, engaged))
    for army_id, army in sorted(world.armies.items()):
        if army_id in engaged:
            continue
        before = army.fatigue
        army.fatigue = max(
            0, before - scenario.tuning.battle.unengaged_fatigue_recovery
        )
        if before != army.fatigue:
            events.append(_recovery_event(army_id, before, army.fatigue))
    record_visible_observations(world, scenario)
    return events
