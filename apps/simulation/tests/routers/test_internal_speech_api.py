from uuid import uuid4

from httpx import AsyncClient
from tests.repositories.helpers import OWNER_USER_ID
from tests.routers.test_scenes_api import INTERNAL, _start

ACTING = "X-Acting-User-Id"
SPEECH = {"speech_text": "Stand with me, and we hold the line."}


async def _grade_path_and_army(api: AsyncClient) -> tuple[str, str]:
    base, _ = await _start(api)
    world = (await api.get(f"{base}/world")).json()
    playthrough_id = base.rsplit("/", 1)[1]
    own = next(
        army["army_id"]
        for army in world["armies"]
        if army["owner_id"] == world["my_faction"]["id"]
    )
    return f"/internal/v1/playthroughs/{playthrough_id}/battle-speech/grade", own


async def test_an_unconfigured_provider_gives_a_neutral_outcome(
    api: AsyncClient,
) -> None:
    path, army_id = await _grade_path_and_army(api)
    response = await api.post(
        path,
        json=SPEECH | {"army_id": army_id},
        headers=INTERNAL | {ACTING: str(OWNER_USER_ID)},
    )
    assert response.status_code == 200
    assert response.json() == {
        "kind": "battle_speech",
        "morale_delta_percent": 0,
        "rubric_scores": {},
    }


async def test_an_unknown_army_is_not_found(api: AsyncClient) -> None:
    path, _ = await _grade_path_and_army(api)
    response = await api.post(
        path,
        json=SPEECH | {"army_id": "nobody"},
        headers=INTERNAL | {ACTING: str(OWNER_USER_ID)},
    )
    assert response.status_code == 404


async def test_another_user_cannot_grade_for_this_playthrough(
    api: AsyncClient,
) -> None:
    path, army_id = await _grade_path_and_army(api)
    response = await api.post(
        path,
        json=SPEECH | {"army_id": army_id},
        headers=INTERNAL | {ACTING: str(uuid4())},
    )
    assert response.status_code == 404


async def test_the_route_needs_the_internal_token(api: AsyncClient) -> None:
    path, army_id = await _grade_path_and_army(api)
    response = await api.post(path, json=SPEECH | {"army_id": army_id})
    assert response.status_code in (401, 403)
