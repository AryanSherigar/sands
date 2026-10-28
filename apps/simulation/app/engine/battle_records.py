from app.models.world_battle import BattleContingent, BattleSide, BattleState
from app.models.world_state import WorldState


def populate_battle_contingents(world: WorldState, battle: BattleState) -> None:
    for side, army_ids in (
        (BattleSide.ATTACKER, battle.attacker_army_ids),
        (BattleSide.DEFENDER, battle.defender_army_ids),
    ):
        _populate_side(world, battle, side, army_ids)


def _populate_side(
    world: WorldState, battle: BattleState, side: BattleSide, army_ids: list[str]
) -> None:
    participants = [
        world.armies[army_id] for army_id in sorted(army_ids) if army_id in world.armies
    ]
    if not participants:
        return
    lead_field = f"{side.value}_lead_faction_id"
    if getattr(battle, lead_field) is None:
        setattr(battle, lead_field, participants[0].owner_id)
    owners = sorted({army.owner_id for army in participants})
    for owner in owners:
        owned = [army for army in participants if army.owner_id == owner]
        if owner not in battle.contingents:
            battle.contingents[owner] = BattleContingent(
                faction_id=owner, side=side, army_ids=[], entry_troops=0
            )
        contingent = battle.contingents[owner]
        new_armies = [army for army in owned if army.id not in contingent.army_ids]
        contingent.entry_troops += sum(sum(army.troops.values()) for army in new_armies)
        contingent.army_ids = sorted(army.id for army in owned)
