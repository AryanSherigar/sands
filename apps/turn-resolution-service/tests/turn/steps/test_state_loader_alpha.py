"""Unit tests for state_loader.assert_alpha_scenario, with the repository mocked."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.config import settings
from app.exceptions.alpha_exceptions import AlphaScenarioOnlyError
from app.turn.steps.state_loader import assert_alpha_scenario


@pytest.fixture
def alpha_scenario_id(monkeypatch) -> uuid.UUID:
    scenario_id = uuid.uuid4()
    monkeypatch.setattr(settings, "is_alpha_mode", True)
    monkeypatch.setattr(settings, "alpha_scenario_id", scenario_id)
    return scenario_id


def repo_returning(
    scenario_id: uuid.UUID | None, snapshot: dict[str, object] | None = None
) -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_id.return_value = (
        None
        if scenario_id is None
        else SimpleNamespace(scenario_id=scenario_id, scenario_snapshot=snapshot or {})
    )
    return repo


async def test_alpha_off_never_touches_the_repository() -> None:
    repo = repo_returning(uuid.uuid4())

    await assert_alpha_scenario(uuid.uuid4(), repo)

    repo.get_by_id.assert_not_awaited()


async def test_alpha_scenario_passes(alpha_scenario_id) -> None:
    await assert_alpha_scenario(uuid.uuid4(), repo_returning(alpha_scenario_id))


async def test_other_scenario_is_refused(alpha_scenario_id) -> None:
    with pytest.raises(AlphaScenarioOnlyError):
        await assert_alpha_scenario(uuid.uuid4(), repo_returning(uuid.uuid4()))


async def test_missing_playthrough_is_left_to_later_steps(alpha_scenario_id) -> None:
    await assert_alpha_scenario(uuid.uuid4(), repo_returning(None))


async def test_a_private_scenario_playthrough_passes(alpha_scenario_id) -> None:
    repo = repo_returning(uuid.uuid4(), {"visibility": "private"})

    await assert_alpha_scenario(uuid.uuid4(), repo)


@pytest.mark.parametrize(
    "snapshot", [{"visibility": "public"}, {}, {"visibility": None}]
)
async def test_a_playthrough_not_pinned_private_is_refused(
    alpha_scenario_id, snapshot
) -> None:
    with pytest.raises(AlphaScenarioOnlyError):
        await assert_alpha_scenario(
            uuid.uuid4(), repo_returning(uuid.uuid4(), snapshot)
        )
