from app.engine.battles.state import PERCENT, contingent_armies
from app.engine.economy.arithmetic import ceil_division, clamp
from app.models.world_army import ArmyState
from app.models.world_battle import BattleContingent
from app.models.world_state import WorldState
from strategy_contracts.battle import BattleTuning, SupplyState


def weighted_attribute(
    world: WorldState, contingent: BattleContingent, name: str
) -> int:
    armies = contingent_armies(world, contingent)
    soldiers = sum(sum(army.troops.values()) for army in armies)
    return sum(
        sum(army.troops.values()) * getattr(army, name) for army in armies
    ) // max(1, soldiers)


def apply_army_strain(
    army: ArmyState,
    casualties: int,
    before: int,
    supply: SupplyState,
    tuning: BattleTuning,
) -> None:
    army.morale = clamp(
        army.morale
        - tuning.morale_base_loss
        - ceil_division(PERCENT * casualties, max(1, before)),
        0,
        PERCENT,
    )
    army.fatigue = min(
        PERCENT,
        army.fatigue
        + tuning.fatigue_per_exchange
        + tuning.supply_extra_fatigue[supply],
    )


def should_withdraw(
    world: WorldState, contingent: BattleContingent, tuning: BattleTuning
) -> bool:
    remaining = sum(
        sum(army.troops.values()) for army in contingent_armies(world, contingent)
    )
    policy = contingent.plan.withdrawal_policy
    return (
        weighted_attribute(world, contingent, "morale")
        <= tuning.withdrawal_morale[policy]
        or (contingent.entry_troops - remaining) * PERCENT
        >= contingent.entry_troops * tuning.withdrawal_loss_percent[policy]
    )
