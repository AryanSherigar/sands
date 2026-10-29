"""Diplomatic stance evaluations and attitude matrix."""

from enum import Enum
from typing import Mapping

from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.ids import FactionId


class DiplomaticAttitude(str, Enum):
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    SUSPICIOUS = "suspicious"
    HOSTILE = "hostile"
    AT_WAR = "at_war"


class DiplomaticStanceRegistry:
    """Registry and matrix for diplomatic attitude evaluations between factions."""

    def __init__(self, world: WorldState | None = None) -> None:
        self._world = world

    def evaluate_attitude(
        self,
        source_faction_id: FactionId,
        target_faction_id: FactionId,
        world: WorldState | None = None,
    ) -> DiplomaticAttitude:
        current_world = world or self._world
        if current_world is None:
            return DiplomaticAttitude.NEUTRAL

        if source_faction_id == target_faction_id:
            return DiplomaticAttitude.FRIENDLY

        for rel in current_world.relations:
            factions = {rel.faction_a, rel.faction_b}
            if source_faction_id in factions and target_faction_id in factions:
                if rel.status == RelationStatus.WAR:
                    return DiplomaticAttitude.AT_WAR
                if rel.status == RelationStatus.ALLIANCE:
                    return DiplomaticAttitude.FRIENDLY

        source = current_world.factions.get(source_faction_id)
        target = current_world.factions.get(target_faction_id)
        if source is None or target is None:
            return DiplomaticAttitude.NEUTRAL

        reputation = getattr(target, "reputation", 0)
        if reputation >= 50:
            return DiplomaticAttitude.FRIENDLY
        elif reputation >= 0:
            return DiplomaticAttitude.NEUTRAL
        elif reputation >= -50:
            return DiplomaticAttitude.SUSPICIOUS
        else:
            return DiplomaticAttitude.HOSTILE

    def build_attitude_matrix(
        self, world: WorldState | None = None
    ) -> dict[FactionId, dict[FactionId, DiplomaticAttitude]]:
        current_world = world or self._world
        if current_world is None:
            return {}

        matrix: dict[FactionId, dict[FactionId, DiplomaticAttitude]] = {}
        faction_ids = sorted(current_world.factions.keys())
        for f1 in faction_ids:
            matrix[f1] = {}
            for f2 in faction_ids:
                matrix[f1][f2] = self.evaluate_attitude(f1, f2, current_world)
        return matrix
