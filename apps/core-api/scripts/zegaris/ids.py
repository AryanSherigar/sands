"""Deterministic ids for the Zegaris scenario (see scripts/seeding/ids.py)."""

import uuid

from scripts.seeding.ids import ScenarioIds

NAMESPACE = uuid.UUID("c41f7a96-2d83-4b0e-8e57-6a19d3f0b2c4")

IDS = ScenarioIds(NAMESPACE, "zegaris-owls-respite")

SCENARIO_ID = IDS.scenario_id
entity_id = IDS.entity_id
entity_ref = IDS.entity_ref
child_id = IDS.child_id
