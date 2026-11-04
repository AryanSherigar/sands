"""Deterministic ids for the appraisal scenario (see scripts/seeding/ids.py)."""

import uuid

from scripts.seeding.ids import ScenarioIds

NAMESPACE = uuid.UUID("3b8e5f2a-9c14-4d7e-a6f1-0e2d9b7c4a58")

IDS = ScenarioIds(NAMESPACE, "reincarnated-aristocrat")

SCENARIO_ID = IDS.scenario_id
entity_id = IDS.entity_id
entity_ref = IDS.entity_ref
child_id = IDS.child_id
