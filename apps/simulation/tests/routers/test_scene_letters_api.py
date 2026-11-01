from httpx import AsyncClient
from strategy_contracts.letters import LetterTuning
from strategy_contracts.scenario import GrudgeSetup
from tests.repositories.helpers import OWNER_USER_ID
from tests.routers.test_scenes_api import INTERNAL, _internal, _scene
from tests.services.helpers import mutation
from tests.services.test_campaign_service import initialization

LETTER_TEXT = "Greetings from Ashford, and a word on the river fords."
WARMER = "letter_warmer"


async def _start_with_letters(api: AsyncClient) -> tuple[str, int]:
    request = initialization()
    request.scenario.tuning.letters = LetterTuning(is_enabled=True)
    request.scenario.starting.grudges.append(
        GrudgeSetup(
            holder_id="mira",
            target_id="valdren",
            opinion=-30,
            reason="Carrow's riders crossed the Ashford fords.",
        )
    )
    body = request.model_dump(mode="json")
    created = await api.post("/internal/v1/playthroughs", json=body, headers=INTERNAL)
    return f"/v1/playthroughs/{body['playthrough_id']}", created.json()["world_version"]


async def _end_turn_into_letter(api: AsyncClient) -> tuple[str, dict, str]:
    base, version = await _start_with_letters(api)
    ended = await api.post(
        f"{base}/end-turn", json=mutation("end", version).model_dump()
    )
    assert ended.status_code == 200
    world = (await api.get(f"{base}/world")).json()
    assert world["status"] == "awaiting_scene"
    return base, world, world["scene_id"]


def _letter_body(text: str = LETTER_TEXT) -> dict:
    return {"text": text}


def _reply(option_id: str | None, action: str = "choose_option") -> dict:
    return {
        "sequence": 2,
        "player_text": "Our bailiffs will walk the line with yours in spring.",
        "leader_text": "The sender's letter was received with care.",
        "decision": {"action": action, "option_id": option_id},
    }


async def _letter_scene(api: AsyncClient):
    base, world, scene_id = await _end_turn_into_letter(api)
    path, headers = _internal(scene_id, OWNER_USER_ID)
    return base, world, scene_id, path, headers


async def test_rollover_arms_a_letter_the_player_can_see(api: AsyncClient) -> None:
    base, world, scene_id, _, _ = await _letter_scene(api)
    view = (await api.get(f"{base}/scenes/{scene_id}")).json()
    assert (view["scene_type"], view["initiator"]) == ("letter", "ai")
    assert (view["status"], view["exchanges_remaining"]) == ("pending", 2)
    blocked = await api.post(
        f"{base}/end-turn",
        json=mutation("end-again", world["world_version"], world["turn"]).model_dump(),
    )
    assert (blocked.status_code, blocked.json()["code"]) == (409, "scene_pending")


async def test_letter_body_is_stored_once_and_second_call_is_duplicate_ignored(
    api: AsyncClient,
) -> None:
    _, _, _, path, headers = await _letter_scene(api)

    first = await api.post(f"{path}/letter", json=_letter_body(), headers=headers)
    second = await api.post(
        f"{path}/letter", json=_letter_body("A different letter."), headers=headers
    )

    assert first.json()["status"] == "accepted"
    assert first.json()["exchanges_remaining"] == 1
    assert second.json()["status"] == "duplicate_ignored"
    package = (await api.get(f"{path}/package", headers=headers)).json()
    assert [item["leader_text"] for item in package["transcript"]] == [LETTER_TEXT]
    assert package["transcript"][0]["player_text"] == ""


async def test_scene_view_returns_the_stored_letter_after_a_reopen(
    api: AsyncClient,
) -> None:
    base, _, scene_id, path, headers = await _letter_scene(api)
    await api.post(f"{path}/letter", json=_letter_body(), headers=headers)

    view = (await api.get(f"{base}/scenes/{scene_id}")).json()

    assert view["transcript"][0]["leader_text"] == LETTER_TEXT


async def test_letter_body_is_refused_for_a_negotiation_scene(api: AsyncClient) -> None:
    _, _, _, path, headers = await _scene(api)
    refused = await api.post(f"{path}/letter", json=_letter_body(), headers=headers)
    assert refused.status_code == 409


async def test_letter_body_needs_the_service_token_and_the_owner(
    api: AsyncClient,
) -> None:
    _, _, _, path, headers = await _letter_scene(api)
    assert (await api.post(f"{path}/letter", json=_letter_body())).status_code == 401
    stranger = {**headers, "X-Acting-User-Id": "00000000-0000-4000-8000-0000000000aa"}
    refused = await api.post(f"{path}/letter", json=_letter_body(), headers=stranger)
    assert refused.status_code == 404


async def test_letter_body_must_not_be_empty(api: AsyncClient) -> None:
    _, _, _, path, headers = await _letter_scene(api)
    refused = await api.post(f"{path}/letter", json={"text": ""}, headers=headers)
    assert refused.status_code == 422


async def test_a_sealed_reply_with_a_known_option_closes_the_scene(
    api: AsyncClient,
) -> None:
    base, _, scene_id, path, headers = await _letter_scene(api)
    await api.post(f"{path}/letter", json=_letter_body(), headers=headers)

    sealed = await api.post(f"{path}/exchanges", json=_reply(WARMER), headers=headers)

    assert sealed.json()["status"] == "accepted"
    assert sealed.json()["scene_status"] == "resolved"
    view = (await api.get(f"{base}/scenes/{scene_id}")).json()
    assert view["outcome"] == {"kind": "choice", "option_id": WARMER}
    assert (await api.get(f"{base}/world")).json()["status"] == "planning"


async def test_a_sealed_reply_with_an_unknown_option_defaults_the_scene(
    api: AsyncClient,
) -> None:
    base, _, scene_id, path, headers = await _letter_scene(api)
    await api.post(f"{path}/letter", json=_letter_body(), headers=headers)

    sealed = await api.post(
        f"{path}/exchanges", json=_reply("gift_gold"), headers=headers
    )

    assert sealed.json()["reason"] == "not_allowed"
    assert sealed.json()["scene_status"] == "defaulted"
    view = (await api.get(f"{base}/scenes/{scene_id}")).json()
    assert view["outcome"] == {"kind": "choice", "option_id": "letter_no_effect"}


async def test_a_sealed_reply_that_proposes_terms_defaults_the_scene(
    api: AsyncClient,
) -> None:
    _, _, _, path, headers = await _letter_scene(api)
    await api.post(f"{path}/letter", json=_letter_body(), headers=headers)
    body = _reply(None, "propose_terms")
    body["decision"]["duration_turns"] = 8

    sealed = await api.post(f"{path}/exchanges", json=body, headers=headers)

    assert sealed.json()["reason"] == "not_allowed"
    assert sealed.json()["scene_status"] == "defaulted"


async def test_declining_a_letter_resolves_it_with_no_effect(api: AsyncClient) -> None:
    base, world, scene_id, _, _ = await _letter_scene(api)
    body = mutation("decline", world["world_version"], world["turn"]).model_dump()

    declined = await api.post(
        f"{base}/scenes/{scene_id}/decision", json=body | {"is_confirmed": False}
    )

    assert declined.status_code == 200
    view = (await api.get(f"{base}/scenes/{scene_id}")).json()
    assert (view["status"], view["outcome"]["option_id"]) == (
        "defaulted",
        "letter_no_effect",
    )
    assert (await api.get(f"{base}/world")).json()["status"] == "planning"


async def test_a_letter_cannot_be_confirmed_like_a_pact(api: AsyncClient) -> None:
    base, world, scene_id, _, _ = await _letter_scene(api)
    body = mutation("confirm", world["world_version"], world["turn"]).model_dump()

    refused = await api.post(
        f"{base}/scenes/{scene_id}/decision",
        json=body | {"is_confirmed": True, "proposal_sequence": 1},
    )

    assert refused.status_code == 422
