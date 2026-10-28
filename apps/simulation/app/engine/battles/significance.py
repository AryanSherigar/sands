from app.models.world_battle import BattleSignificance, BattleState
from app.models.world_state import WorldState

SIGNIFICANT_COMMITMENT_PERCENT = 30


def classify_battle(world: WorldState, battle: BattleState) -> None:
    reasons = _region_reasons(world, battle)
    reasons.update(_commitment_reasons(world, battle))
    if _has_important_commander(world, battle):
        reasons.add(BattleSignificance.IMPORTANT_COMMANDER)
    battle.significance_reasons = sorted(reasons, key=lambda reason: reason.value)
    battle.is_big = bool(reasons)


def _region_reasons(world: WorldState, battle: BattleState) -> set[BattleSignificance]:
    region = world.regions[battle.region_id]
    reasons: set[BattleSignificance] = set()
    if region.claimant_ids:
        reasons.add(BattleSignificance.CLAIMED_REGION)
    if any(
        faction.capital_region_id == battle.region_id
        for faction in world.factions.values()
    ):
        reasons.add(BattleSignificance.CAPITAL_REGION)
    return reasons


def _commitment_reasons(
    world: WorldState, battle: BattleState
) -> set[BattleSignificance]:
    for contingent in battle.contingents.values():
        committed = sum(
            sum(world.armies[army_id].troops.values())
            for army_id in contingent.army_ids
        )
        total = sum(
            sum(army.troops.values())
            for army in world.armies.values()
            if army.owner_id == contingent.faction_id
        )
        if total and committed * 100 >= total * SIGNIFICANT_COMMITMENT_PERCENT:
            return {BattleSignificance.COMMITTED_STRENGTH}
    return set()


def _has_important_commander(world: WorldState, battle: BattleState) -> bool:
    army_ids = battle.attacker_army_ids + battle.defender_army_ids
    return any(
        army.commander_id in world.commanders
        and world.commanders[army.commander_id].is_important
        for army_id in army_ids
        if (army := world.armies.get(army_id)) is not None
    )
