from app.models.world_state import WorldState


def clear_vassalage_state(world: WorldState, vassalage_id: str) -> None:
    vassal = world.vassal
    vassal.demands = [i for i in vassal.demands if i.vassalage_id != vassalage_id]
    vassal.consents = [i for i in vassal.consents if i.vassalage_id != vassalage_id]
    vassal.standing = [i for i in vassal.standing if i.vassalage_id != vassalage_id]
    vassal.last_demand_turn.pop(vassalage_id, None)
    vassal.garrison_until.pop(vassalage_id, None)
    world.alliance.calls = [
        i for i in world.alliance.calls if i.alliance_id != vassalage_id
    ]
