"""Client effects and authored images fired by conditions, through the real
pipeline: emitted before narration, the image persisted, alpha mode no bar."""

import json

import pytest
from app.config import settings
from app.db.models.turn_log import TurnLog
from app.turn.steps import ai_orchestrator
from pipeline_seed import narrator, seed_master_playthrough, take_turn
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio(loop_scope="session")

POSTER_URL = "https://media.example/night-desk/truefeel-poster.png"
EFFECT = {
    "kind": "input_takeover",
    "params": {
        "text": "Get me out of here, Orr",
        "lock_ms": 4500,
        "type_ms_per_char": 60,
    },
}


def _snapshot() -> dict[str, object]:
    return {
        "mode": "master",
        "narrator_persona": "Quiet.",
        "world_data": {},
        "state_schema": {"clock": {"type": "number", "min": 0, "max": 100}},
        "entities": [],
        "rule_invariants": [],
        "scenario_conditions": [
            {
                "condition_id": "c-effect",
                "label": "Effect",
                "condition_expression": {"field": "clock", "op": ">=", "value": 0},
                "narrator_instruction": "",
                "metadata": {
                    "client_effect": EFFECT,
                    "authored_image_url": POSTER_URL,
                },
            }
        ],
    }


async def test_effect_and_authored_image_reach_the_client(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        narrator("A poster hangs by the lift."),
    )
    playthrough, participant = await seed_master_playthrough(
        db_session, _snapshot(), {"clock": 0}
    )
    monkeypatch.setattr(settings, "is_alpha_mode", True)
    monkeypatch.setattr(settings, "alpha_scenario_id", playthrough.scenario_id)

    events = await take_turn(db_session, playthrough, participant)

    names = [event.event for event in events]
    assert names.index("client_effect") < names.index("narration")
    effect = next(e for e in events if e.event == "client_effect")
    assert json.loads(effect.data) == EFFECT
    image = next(e for e in events if e.event == "scene_image")
    assert image.data == POSTER_URL
    stored = (
        await db_session.execute(
            select(TurnLog).where(TurnLog.playthrough_id == playthrough.playthrough_id)
        )
    ).scalar_one()
    assert stored.image_url == POSTER_URL
