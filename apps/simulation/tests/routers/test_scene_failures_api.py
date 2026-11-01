from uuid import uuid4

from httpx import AsyncClient
from strategy_contracts.scene import ChoiceOutcome, ChoiceSpec, ScenePackage
from tests.repositories.helpers import OWNER_USER_ID
from tests.routers.test_scene_triggers_api import _end_turn_into_offer
from tests.routers.test_scenes_api import INTERNAL, _exchange, _scene

MAX_FAILURES = 3


async def _fail(api: AsyncClient, path: str, headers: dict[str, str]) -> dict:
    response = await api.post(f"{path}/failures", headers=headers)
    assert response.status_code == 200
    return response.json()


async def test_repeated_failures_close_the_scene_with_its_default_outcome(
    api: AsyncClient,
) -> None:
    base, _, scene_id, path, headers = await _scene(api)
    first = await _fail(api, path, headers)
    assert (first["failed_attempts"], first["attempts_remaining"]) == (1, 2)
    await _fail(api, path, headers)
    last = await _fail(api, path, headers)
    assert (last["scene_status"], last["attempts_remaining"]) == ("defaulted", 0)
    view = (await api.get(f"{base}/scenes/{scene_id}")).json()
    assert (view["status"], view["outcome"]["result"]) == ("defaulted", "refused")
    assert (await api.get(f"{base}/world")).json()["status"] == "planning"


async def test_a_recorded_exchange_resets_the_failure_count(api: AsyncClient) -> None:
    _, _, _, path, headers = await _scene(api)
    await _fail(api, path, headers)
    await _fail(api, path, headers)
    await api.post(f"{path}/exchanges", json=_exchange(1), headers=headers)
    again = await _fail(api, path, headers)
    assert again["failed_attempts"] == 1
    assert again["scene_status"] in ("pending", "opened")


async def test_a_forced_offer_cannot_deadlock_when_the_narrator_keeps_failing(
    api: AsyncClient,
) -> None:
    base, _, scene_id = await _end_turn_into_offer(api, is_declinable=False)
    path = f"/internal/v1/scenes/{scene_id}"
    headers = INTERNAL | {"X-Acting-User-Id": str(OWNER_USER_ID)}
    for _ in range(MAX_FAILURES):
        await _fail(api, path, headers)
    assert (await api.get(f"{base}/world")).json()["status"] == "planning"


async def test_failures_after_the_scene_ended_are_not_counted(api: AsyncClient) -> None:
    _, _, _, path, headers = await _scene(api)
    await api.post(f"{path}/exchanges", json=_exchange(1, "walk_out"), headers=headers)
    result = await _fail(api, path, headers)
    assert (result["scene_status"], result["failed_attempts"]) == ("resolved", 0)


async def test_failure_reports_need_the_service_token_and_the_owner(
    api: AsyncClient,
) -> None:
    _, _, _, path, headers = await _scene(api)
    assert (await api.post(f"{path}/failures")).status_code == 401
    stranger = {**headers, "X-Acting-User-Id": str(uuid4())}
    assert (await api.post(f"{path}/failures", headers=stranger)).status_code == 404


def test_a_package_whose_default_is_not_an_allowed_option_is_refused() -> None:
    import pytest
    from app.exceptions.scene_exceptions import InvalidScenePackageError
    from app.services.scene_package_validation import require_valid_package
    from strategy_contracts.scene import ChoiceOption, SceneSituation, SceneType

    package = ScenePackage(
        scene_id=uuid4(),
        playthrough_id=uuid4(),
        scene_type=SceneType.EVENT,
        turn=1,
        situation=SceneSituation(summary="x"),
        allowed_outcomes=[ChoiceSpec(options=[ChoiceOption(id="option_a", label="A")])],
        exchange_cap=0,
        default_outcome=ChoiceOutcome(option_id="option_missing"),
    )
    with pytest.raises(InvalidScenePackageError):
        require_valid_package(package)
