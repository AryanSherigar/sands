from collections.abc import Mapping
from typing import TypeVar

from app.models.world_battle import BattleState
from app.models.world_state import WorldState

ValueT = TypeVar("ValueT")


def sorted_items(mapping: Mapping[str, ValueT]) -> list[tuple[str, ValueT]]:
    return sorted(mapping.items(), key=lambda item: item[0])


def canonicalize_lists(world: WorldState) -> None:
    # NOTE: sorted by plain string key, so counter ids order lexically
    # ("x_10" before "x_9"); stable and deterministic, which is all the hash needs.
    world.relations.sort(key=lambda item: (item.faction_a, item.faction_b))
    world.truces.sort(key=lambda item: (item.faction_a, item.faction_b, item.id))
    world.commitments.sort(key=lambda item: item.id)
    world.oathbreakers.sort(key=lambda item: item.faction_id)
    world.plays.sort(key=lambda item: item.id)
    world.wars.sort(key=lambda item: item.id)
    world.outrage.sort(key=lambda item: item.faction_id)
    world.prisoners.sort(key=lambda item: item.id)
    world.envoys.sort(key=lambda item: item.id)
    world.grounds.sort(key=lambda item: item.id)
    world.pressure.mediation_offers.sort(key=lambda item: item.id)
    world.pressure.subsidies.sort(key=lambda item: item.id)
    world.pressure.rumors.sort(key=lambda item: item.id)
    world.peace.hostages.sort(key=lambda item: item.id)
    world.peace.breach.sort(key=lambda item: (item.faction_a, item.faction_b))
    world.peace.lapses.sort(key=lambda item: item.truce_id)
    world.alliance.calls.sort(key=lambda item: item.id)
    world.alliance.standing.sort(key=lambda item: item.alliance_id)
    world.vassal.demands.sort(key=lambda item: item.id)
    world.vassal.consents.sort(
        key=lambda item: (item.vassalage_id, item.action, item.target_faction_id)
    )
    world.vassal.standing.sort(key=lambda item: item.vassalage_id)
    world.coalition.coalitions.sort(key=lambda item: item.id)
    world.coalition.conquests.sort(key=lambda item: (item.turn, item.faction_id))
    for coalition in world.coalition.coalitions:
        coalition.member_ids.sort()
    world.pending_events.sort(key=lambda item: item.id)
    world.event_memories.sort(key=lambda item: (item.template_id, item.subject_id))
    world.battles.sort(key=lambda item: item.id)
    world.accepted_commands.sort(key=lambda item: item.id)
    for battle in world.battles:
        _canonicalize_battle_lists(battle)


def _canonicalize_battle_lists(battle: BattleState) -> None:
    battle.attacker_army_ids.sort()
    battle.defender_army_ids.sort()
    battle.report_ids.sort()
    battle.mission_ids.sort()
    battle.capture_ids.sort()
    battle.deferred_command_ids.sort()
    for contingent in battle.contingents.values():
        contingent.army_ids.sort()
