from uuid import UUID, uuid4

import pytest
from app.engine import scene_closing
from app.engine.hashing import world_hash
from app.engine.replay import replay_history
from app.engine.scene_closing import close_scene
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.battle_progress import OperationGuard
from app.models.replay import ReplayStep, ResolveSceneReplayInput
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import (
    ChoiceOutcome,
    ProseOnlyOutcome,
    SceneOutcome,
    SceneType,
)

from tests.engine.test_negotiation import _world
from tests.models.builders import PLAYTHROUGH_ID

SCENARIO = load_three_crowns()
GUARD = OperationGuard(
    operation_id="op-1", expected_world_version=1, expected_turn=4, expected_wave=0
)


def _grant_treasury(
    world: WorldState,
    scenario: StrategyScenario,
    scene_id: UUID,
    outcome: SceneOutcome,
) -> tuple[WorldState, list[EventLogEntry]]:
    closed = world.model_copy(deep=True)
    faction = next(item for item in closed.factions.values() if item.is_player)
    faction.treasury += 7
    return closed, []


def test_an_unregistered_scene_type_cannot_close() -> None:
    with pytest.raises(CampaignProgressError):
        close_scene(
            _world(["pragmatic"]),
            SCENARIO,
            SceneType.REVOLT_TALK,
            uuid4(),
            ChoiceOutcome(option_id="concessions"),
        )


def test_a_negotiation_scene_refuses_an_outcome_that_is_not_terms() -> None:
    with pytest.raises(CampaignProgressError):
        close_scene(
            _world(["pragmatic"]),
            SCENARIO,
            SceneType.NEGOTIATION,
            uuid4(),
            ProseOnlyOutcome(),
        )


def test_a_registered_closer_applies_through_replay(monkeypatch) -> None:
    monkeypatch.setitem(
        scene_closing.SCENE_CLOSERS, SceneType.REVOLT_TALK, _grant_treasury
    )
    start = _world(["pragmatic"])
    scene_id = uuid4()
    outcome = ChoiceOutcome(option_id="concessions")
    closed, _ = close_scene(start, SCENARIO, SceneType.REVOLT_TALK, scene_id, outcome)
    step = ReplayStep(
        playthrough_id=PLAYTHROUGH_ID,
        sequence=1,
        operation_id="op-1",
        kind="resolve_scene",
        input=ResolveSceneReplayInput(
            guard=GUARD,
            scene_id=scene_id,
            scene_type=SceneType.REVOLT_TALK,
            outcome=outcome,
        ),
        before_hash=world_hash(start),
        after_hash=world_hash(closed),
        turn=4,
        wave=0,
    )

    result = replay_history(start, SCENARIO, [step])

    assert result.world_hash == world_hash(closed)
    assert world_hash(closed) != world_hash(start)
