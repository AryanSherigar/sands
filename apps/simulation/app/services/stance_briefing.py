import hashlib
import json

from app.engine.stances.menu import resolve_stance_menu
from app.models.stance import StanceBriefing, StanceMenuItem
from app.models.world_character import LeaderState, OpinionState
from app.models.world_state import WorldState
from app.services.trait_notes import trait_notes
from strategy_contracts.ids import LeaderId
from strategy_contracts.scenario import StrategyScenario

MAX_BRIEFING_MEMORIES = 5
MAX_BRIEFING_OPINIONS = 3


def build_stance_briefing(
    world: WorldState, scenario: StrategyScenario, leader_id: LeaderId
) -> StanceBriefing:
    leader = world.leaders[leader_id]
    ambitions = {item.id: item.name for item in scenario.ambitions}
    menu = resolve_stance_menu(scenario, leader.faction_id)
    return StanceBriefing(
        leader_name=leader.name,
        trait_notes=trait_notes(leader.trait_ids, scenario),
        ambitions=[ambitions.get(item, item) for item in leader.ambition_ids],
        memories=_memory_lines(leader),
        opinions=_opinion_lines(world, leader),
        current_option_id=world.factions[leader.faction_id].stance.option_id,
        menu=[
            StanceMenuItem(
                id=stance.id, name=stance.name, description=stance.description
            )
            for stance in menu
        ],
    )


def _memory_lines(leader: LeaderState) -> list[str]:
    ordered = sorted(leader.memories, key=lambda memory: (memory.turn, memory.kind))
    return [f"turn {memory.turn}: {memory.kind}" for memory in ordered][
        -MAX_BRIEFING_MEMORIES:
    ]


def _opinion_lines(world: WorldState, leader: LeaderState) -> list[str]:
    totals = {
        target_id: _opinion_total(opinion)
        for target_id, opinion in leader.opinions.items()
    }
    strongest = sorted(
        totals, key=lambda target_id: (-abs(totals[target_id]), target_id)
    )
    return [
        f"{_leader_name(world, target_id)}: {totals[target_id]:+d}"
        for target_id in strongest[:MAX_BRIEFING_OPINIONS]
    ]


def _opinion_total(opinion: OpinionState) -> int:
    return sum(reason.value for reason in opinion.reasons)


def _leader_name(world: WorldState, leader_id: LeaderId) -> str:
    target = world.leaders.get(leader_id)
    return target.name if target is not None else leader_id


def stance_input_hash(briefing: StanceBriefing) -> str:
    encoded = json.dumps(
        briefing.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
