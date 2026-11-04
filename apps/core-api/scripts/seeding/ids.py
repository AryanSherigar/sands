"""Deterministic ids so re-seeding is idempotent and rows can reference one
another (conditions to entities, pins to entities) before anything is inserted.

Each scenario needs its own namespace: entity ids are derived from the slug
alone, so two scenarios sharing a namespace would collide on the entity key.
"""

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioIds:
    namespace: uuid.UUID
    scenario_key: str

    @property
    def scenario_id(self) -> uuid.UUID:
        return uuid.uuid5(self.namespace, f"scenario:{self.scenario_key}")

    def entity_id(self, slug: str) -> uuid.UUID:
        return uuid.uuid5(self.namespace, f"entity:{slug}")

    def entity_ref(self, slug: str) -> str:
        """The string form that state fields of type entity_ref hold."""
        return str(self.entity_id(slug))

    def child_id(self, kind: str, key: int | str) -> uuid.UUID:
        return uuid.uuid5(self.namespace, f"{kind}:{key}")
