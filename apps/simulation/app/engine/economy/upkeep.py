from app.engine.economy.arithmetic import ceil_division, percent_of
from app.models.world_army import ArmyState
from app.models.world_state import WorldState
from strategy_contracts.ids import ArmyId, FactionId
from strategy_contracts.scenario import EconomyTuning


def army_upkeep(army: ArmyState, tuning: EconomyTuning) -> int:
    raw = sum(
        count * tuning.upkeep_per_unit[troop_type]
        for troop_type, count in army.troops.items()
    )
    paid = percent_of(raw, tuning.pay_level_percent[army.pay_level])
    return ceil_division(paid, tuning.upkeep_troop_unit)


def faction_upkeep(
    world: WorldState, tuning: EconomyTuning, faction_id: FactionId
) -> dict[ArmyId, int]:
    return {
        army_id: army_upkeep(army, tuning)
        for army_id, army in sorted(world.armies.items())
        if army.owner_id == faction_id
    }
