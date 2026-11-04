"""Night Desk's deterministic ids (see scripts/seeding/ids.py for why)."""

import uuid

from scripts.seeding.ids import ScenarioIds

NAMESPACE = uuid.UUID("7d0a2c1e-5b3f-4e8a-9c61-2f4d8b6a1e90")

IDS = ScenarioIds(NAMESPACE, "night-desk-floor-9")

SCENARIO_ID = IDS.scenario_id
entity_id = IDS.entity_id
entity_ref = IDS.entity_ref
child_id = IDS.child_id
