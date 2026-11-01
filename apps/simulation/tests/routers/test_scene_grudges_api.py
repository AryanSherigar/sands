from httpx import AsyncClient
from strategy_contracts.scenario import GrudgeSetup
from tests.repositories.helpers import OWNER_USER_ID
from tests.routers.test_scenes_api import INTERNAL, _internal, _open
from tests.services.test_campaign_service import initialization

GRUDGE_TEXT = "You burned our granaries."


async def _scene_with_grudge(api: AsyncClient):
    request = initialization()
    request.scenario.starting.grudges.append(
        GrudgeSetup(
            holder_id="mira", target_id="valdren", opinion=-40, reason=GRUDGE_TEXT
        )
    )
    body = request.model_dump(mode="json")
    created = await api.post("/internal/v1/playthroughs", json=body, headers=INTERNAL)
    base = f"/v1/playthroughs/{body['playthrough_id']}"
    opened = await _open(api, base, created.json()["world_version"])
    path, headers = _internal(opened.json()["scene_id"], OWNER_USER_ID)
    return base, opened.json()["scene_id"], path, headers


def _exchange(sequence: int, cited: list[str]) -> dict:
    return {
        "sequence": sequence,
        "player_text": f"player {sequence}",
        "leader_text": f"leader {sequence}",
        "decision": {"action": "continue_talk", "cited_grudge_ids": cited},
    }


async def test_the_package_carries_the_leaders_grudge_with_an_id(
    api: AsyncClient,
) -> None:
    _, _, path, headers = await _scene_with_grudge(api)

    package = (await api.get(f"{path}/package", headers=headers)).json()["package"]

    [grudge] = package["hidden_limits"]["grudges"]
    assert (grudge["id"], grudge["text"]) == ("g1", GRUDGE_TEXT)


async def test_a_grudge_is_hidden_from_the_player_until_it_is_voiced(
    api: AsyncClient,
) -> None:
    base, scene_id, path, headers = await _scene_with_grudge(api)
    await api.post(f"{path}/exchanges", json=_exchange(1, []), headers=headers)

    view = (await api.get(f"{base}/scenes/{scene_id}")).json()

    assert view["voiced_grudges"] == []
    assert GRUDGE_TEXT not in str(view)


async def test_a_voiced_grudge_reaches_the_player_without_hidden_numbers(
    api: AsyncClient,
) -> None:
    base, scene_id, path, headers = await _scene_with_grudge(api)
    await api.post(f"{path}/exchanges", json=_exchange(1, ["g1"]), headers=headers)

    view = await api.get(f"{base}/scenes/{scene_id}")

    [grudge] = view.json()["voiced_grudges"]
    assert grudge["text"] == GRUDGE_TEXT
    assert grudge["band"] == "firm"
    assert set(grudge) == {"text", "band", "is_inherited", "predecessor_name"}
    assert "hidden_limits" not in view.text


async def test_unknown_cited_ids_are_dropped_and_repeats_listed_once(
    api: AsyncClient,
) -> None:
    base, scene_id, path, headers = await _scene_with_grudge(api)
    await api.post(
        f"{path}/exchanges", json=_exchange(1, ["g9", "g1"]), headers=headers
    )
    await api.post(f"{path}/exchanges", json=_exchange(2, ["g1"]), headers=headers)

    view = (await api.get(f"{base}/scenes/{scene_id}")).json()

    assert [item["text"] for item in view["voiced_grudges"]] == [GRUDGE_TEXT]


async def test_the_voiced_list_survives_a_refresh(api: AsyncClient) -> None:
    base, scene_id, path, headers = await _scene_with_grudge(api)
    await api.post(f"{path}/exchanges", json=_exchange(1, ["g1"]), headers=headers)

    first = (await api.get(f"{base}/scenes/{scene_id}")).json()
    second = (await api.get(f"{base}/scenes/{scene_id}")).json()

    assert first["voiced_grudges"] == second["voiced_grudges"] != []
