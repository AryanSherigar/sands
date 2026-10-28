from collections.abc import Mapping

from app.models.stance import StanceChoice
from app.models.world_faction import StanceState
from app.models.world_state import WorldState
from strategy_contracts.ids import LeaderId


def apply_due_stances(
    world: WorldState, recorded: Mapping[LeaderId, StanceChoice]
) -> None:
    for leader_id in sorted(recorded):
        choice = recorded[leader_id]
        if _is_applicable(world, choice):
            world.factions[choice.faction_id].stance = StanceState(
                option_id=choice.option_id, chosen_turn=world.clock.turn
            )


def _is_applicable(world: WorldState, choice: StanceChoice) -> bool:
    faction = world.factions.get(choice.faction_id)
    return (
        choice.due_turn == world.clock.turn
        and faction is not None
        and faction.leader_id == choice.leader_id
        and choice.leader_id in world.leaders
    )
