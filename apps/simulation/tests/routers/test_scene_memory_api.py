from httpx import AsyncClient
from tests.routers.test_scenes_api import _exchange, _open, _scene
from tests.services.helpers import mutation


async def _package(api: AsyncClient, path: str, headers: dict[str, str]) -> dict:
    response = await api.get(f"{path}/package", headers=headers)
    assert response.status_code == 200
    return response.json()["package"]


async def test_a_broken_off_talk_is_remembered_in_the_next_scene(
    api: AsyncClient,
) -> None:
    base, _, _, path, headers = await _scene(api)
    first = await _package(api, path, headers)
    assert first["participants"][0]["memory_notes"] == []
    assert first["participants"][0]["trait_notes"]
    await api.post(f"{path}/exchanges", json=_exchange(1, "walk_out"), headers=headers)

    world = (await api.get(f"{base}/world")).json()
    reopened = await _open(api, base, world["world_version"], "talk-again")
    assert reopened.status_code == 200
    second_path = f"/internal/v1/scenes/{reopened.json()['scene_id']}"
    second = await _package(api, second_path, headers)

    notes = second["participants"][0]["memory_notes"]
    assert len(notes) == 1
    assert "broke off talks" in notes[0]
    assert notes[0].endswith("this turn.")
    assert (
        second["hidden_limits"]["acceptance"]["accept_at"]
        > first["hidden_limits"]["acceptance"]["accept_at"]
    )


async def test_replay_verification_passes_after_a_remembered_refusal(
    api: AsyncClient,
) -> None:
    base, _, _, path, headers = await _scene(api)
    await api.post(f"{path}/exchanges", json=_exchange(1, "refuse"), headers=headers)
    world = (await api.get(f"{base}/world")).json()
    ended = await api.post(
        f"{base}/end-turn",
        json=mutation("end", world["world_version"], world["turn"]).model_dump(),
    )
    assert ended.status_code == 200
    verified = await api.post(f"{base}/replay/verify")
    assert verified.status_code == 200
