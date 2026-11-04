"""Deterministic id for the Aldermark scenario (see scripts/seeding/ids.py)."""

import uuid

from scripts.seeding.ids import ScenarioIds

NAMESPACE = uuid.UUID("2e50c689-e4b2-4056-9fcd-51536dbb4d72")

IDS = ScenarioIds(NAMESPACE, "aldermark")

SCENARIO_ID = IDS.scenario_id
