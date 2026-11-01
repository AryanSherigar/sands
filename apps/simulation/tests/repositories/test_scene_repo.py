from uuid import uuid4

import pytest
from app.exceptions.scene_exceptions import InvalidSceneTransitionError
from app.repositories import scene_repo
from strategy_contracts.scene import (
    ProseOnlyOutcome,
    SceneStatus,
    TermsCardOutcome,
    TermsResult,
)

from tests.models.builders import PLAYTHROUGH_ID
from tests.repositories.helpers import make_package, seed_playthrough

OUTCOME_A = TermsCardOutcome(result=TermsResult.REFUSED)
OUTCOME_B = ProseOnlyOutcome()


async def test_insert_stores_a_pending_scene(db_connection) -> None:
    await seed_playthrough(db_connection)
    package = make_package()
    assert await scene_repo.insert_scene(db_connection, package) is True
    assert await scene_repo.insert_scene(db_connection, package) is False
    row = await scene_repo.get_scene(db_connection, package.scene_id)
    assert row.status is SceneStatus.PENDING
    assert row.package == package
    assert row.outcome is None


async def test_open_scene_lookup_follows_the_lifecycle(db_connection) -> None:
    await seed_playthrough(db_connection)
    package = make_package()
    await scene_repo.insert_scene(db_connection, package)
    open_scene = await scene_repo.get_open_scene(db_connection, PLAYTHROUGH_ID)
    assert open_scene.scene_id == package.scene_id
    await scene_repo.resolve_scene(
        db_connection, package.scene_id, SceneStatus.RESOLVED, OUTCOME_A
    )
    assert await scene_repo.get_open_scene(db_connection, PLAYTHROUGH_ID) is None


async def test_mark_opened_only_from_pending(db_connection) -> None:
    await seed_playthrough(db_connection)
    package = make_package()
    await scene_repo.insert_scene(db_connection, package)
    first = await scene_repo.mark_scene_opened(db_connection, package.scene_id)
    second = await scene_repo.mark_scene_opened(db_connection, package.scene_id)
    assert (first, second) == (True, False)


async def test_second_resolution_is_ignored_and_first_outcome_survives(
    db_connection,
) -> None:
    await seed_playthrough(db_connection)
    package = make_package()
    await scene_repo.insert_scene(db_connection, package)
    first = await scene_repo.resolve_scene(
        db_connection, package.scene_id, SceneStatus.RESOLVED, OUTCOME_A
    )
    second = await scene_repo.resolve_scene(
        db_connection, package.scene_id, SceneStatus.DEFAULTED, OUTCOME_B
    )
    row = await scene_repo.get_scene(db_connection, package.scene_id)
    assert (first, second) == (True, False)
    assert row.status is SceneStatus.RESOLVED
    assert row.outcome == OUTCOME_A
    assert row.resolved_at is not None


async def test_resolving_into_a_non_final_status_is_refused(db_connection) -> None:
    await seed_playthrough(db_connection)
    package = make_package()
    await scene_repo.insert_scene(db_connection, package)
    with pytest.raises(InvalidSceneTransitionError):
        await scene_repo.resolve_scene(
            db_connection, package.scene_id, SceneStatus.OPENED, OUTCOME_A
        )


async def test_unknown_scene(db_connection) -> None:
    assert await scene_repo.get_scene(db_connection, uuid4()) is None
    assert (
        await scene_repo.resolve_scene(
            db_connection, uuid4(), SceneStatus.RESOLVED, OUTCOME_A
        )
        is False
    )
