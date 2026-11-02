import json
from uuid import UUID

from app.engine.hashing import canonical_world_json, world_hash
from app.engine.world_document import world_from_document
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from app.repositories import world_state_repo
from httpx import AsyncClient
from psycopg import AsyncConnection
from strategy_contracts.judgment import JudgmentTuning
from tests.repositories.helpers import OWNER_USER_ID
from tests.routers.test_scenes_api import INTERNAL, _internal, _scene
from tests.services.helpers import mutation
from tests.services.test_campaign_service import initialization

OPENING_TEXT = "The great iron doors have closed behind the guard company."
CAPTIVE_ID = "captive_orrin"


def _talk(sequence: int) -> dict:
    return {
        "sequence": sequence,
        "player_text": f"player {sequence}",
        "leader_text": f"reply {sequence}",
        "decision": {"action": "continue_talk"},
    }


def _pronouncement(
    verdict: str | None, nuance: str | None = None, sequence: int = 2
) -> dict:
    return {
        "sequence": sequence,
        "player_text": "I decree it.",
        "leader_text": "The hall hears the sentence.",
        "decision": {
            "action": "choose_option",
            "option_id": verdict,
            "nuance_id": nuance,
        },
    }


async def _seed_captive(connection: AsyncConnection, playthrough_id: str) -> None:
    identity = UUID(playthrough_id)
    row = await world_state_repo.get_world_state(connection, identity)
    world = world_from_document(row.document)
    world.prisoners.append(
        PrisonerState(
            id=CAPTIVE_ID,
            held_by_id="house_carrow",
            origin_faction_id="house_ashford",
            kind=PrisonerKind.CHARACTER,
            character_id="ser_orrin",
        )
    )
    await world_state_repo.update_world_state(
        connection,
        identity,
        row.row_version,
        row.schema_version,
        row.turn,
        world_hash(world),
        json.loads(canonical_world_json(world)),
    )
    await connection.commit()


async def _end_turn_into_judgment(api: AsyncClient, connection: AsyncConnection):
    request = initialization()
    request.scenario.tuning.judgments = JudgmentTuning(is_enabled=True)
    body = request.model_dump(mode="json")
    await api.post("/internal/v1/playthroughs", json=body, headers=INTERNAL)
    base = f"/v1/playthroughs/{body['playthrough_id']}"
    await _seed_captive(connection, body["playthrough_id"])
    version = (await api.get(f"{base}/world")).json()["world_version"]
    ended = await api.post(
        f"{base}/end-turn", json=mutation("end", version).model_dump()
    )
    assert ended.status_code == 200
    world = (await api.get(f"{base}/world")).json()
    assert world["status"] == "awaiting_scene"
    path, headers = _internal(world["scene_id"], OWNER_USER_ID)
    return base, world, world["scene_id"], path, headers


async def test_rollover_arms_a_judgment_the_player_can_see(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base, world, scene_id, _, _ = await _end_turn_into_judgment(api, db_connection)
    view = (await api.get(f"{base}/scenes/{scene_id}")).json()
    assert (view["scene_type"], view["initiator"]) == ("judgment", "ai")
    assert (view["status"], view["exchanges_remaining"]) == ("pending", 6)
    blocked = await api.post(
        f"{base}/end-turn",
        json=mutation("end-again", world["world_version"], world["turn"]).model_dump(),
    )
    assert (blocked.status_code, blocked.json()["code"]) == (409, "scene_pending")


async def test_opening_is_stored_once_and_a_repeat_is_duplicate_ignored(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base, _, scene_id, path, headers = await _end_turn_into_judgment(api, db_connection)
    first = await api.post(
        f"{path}/opening", json={"text": OPENING_TEXT}, headers=headers
    )
    second = await api.post(
        f"{path}/opening", json={"text": "Another."}, headers=headers
    )
    assert first.json()["status"] == "accepted"
    assert first.json()["exchanges_remaining"] == 5
    assert second.json()["status"] == "duplicate_ignored"
    view = (await api.get(f"{base}/scenes/{scene_id}")).json()
    assert [item["leader_text"] for item in view["transcript"]] == [OPENING_TEXT]


async def test_opening_is_refused_for_a_negotiation_scene(api: AsyncClient) -> None:
    _, _, _, path, headers = await _scene(api)
    refused = await api.post(
        f"{path}/opening", json={"text": OPENING_TEXT}, headers=headers
    )
    assert refused.status_code == 409


async def test_opening_needs_the_service_token_and_the_owner(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    _, _, _, path, headers = await _end_turn_into_judgment(api, db_connection)
    assert (
        await api.post(f"{path}/opening", json={"text": OPENING_TEXT})
    ).status_code == 401
    stranger = {**headers, "X-Acting-User-Id": "00000000-0000-4000-8000-0000000000aa"}
    refused = await api.post(
        f"{path}/opening", json={"text": OPENING_TEXT}, headers=stranger
    )
    assert refused.status_code == 404


async def test_a_pronounced_verdict_resolves_the_scene_and_frees_the_captive(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base, _, scene_id, path, headers = await _end_turn_into_judgment(api, db_connection)
    await api.post(f"{path}/opening", json={"text": OPENING_TEXT}, headers=headers)
    sealed = await api.post(
        f"{path}/exchanges",
        json=_pronouncement("release", "under_oath"),
        headers=headers,
    )
    assert sealed.json()["scene_status"] == "resolved"
    view = (await api.get(f"{base}/scenes/{scene_id}")).json()
    assert view["outcome"] == {
        "kind": "judgment",
        "verdict": "release",
        "nuance": "under_oath",
    }
    assert (await api.get(f"{base}/world")).json()["status"] == "planning"
    row = await world_state_repo.get_world_state(
        db_connection, UUID(base.rsplit("/", 1)[1])
    )
    assert world_from_document(row.document).prisoners == []


async def test_an_unknown_verdict_is_plain_talk_until_the_exchange_cap_defaults_it(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base, _, scene_id, path, headers = await _end_turn_into_judgment(api, db_connection)
    await api.post(f"{path}/opening", json={"text": OPENING_TEXT}, headers=headers)
    early = await api.post(
        f"{path}/exchanges", json=_pronouncement("banish"), headers=headers
    )
    assert (early.json()["reason"], early.json()["scene_status"]) == (
        "not_allowed",
        "opened",
    )
    for sequence in range(3, 6):
        await api.post(f"{path}/exchanges", json=_talk(sequence), headers=headers)
    last = await api.post(
        f"{path}/exchanges", json=_pronouncement("banish", sequence=6), headers=headers
    )
    assert last.json()["scene_status"] == "defaulted"
    view = (await api.get(f"{base}/scenes/{scene_id}")).json()
    assert (view["status"], view["outcome"]["verdict"]) == ("defaulted", "imprison")


async def test_declining_closes_with_the_default_and_confirming_is_refused(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base, world, scene_id, _, _ = await _end_turn_into_judgment(api, db_connection)
    body = mutation("confirm", world["world_version"], world["turn"]).model_dump()
    refused = await api.post(
        f"{base}/scenes/{scene_id}/decision",
        json=body | {"is_confirmed": True, "proposal_sequence": 1},
    )
    assert refused.status_code == 422
    body = mutation("decline", world["world_version"], world["turn"]).model_dump()
    declined = await api.post(
        f"{base}/scenes/{scene_id}/decision", json=body | {"is_confirmed": False}
    )
    assert declined.status_code == 200
    view = (await api.get(f"{base}/scenes/{scene_id}")).json()
    assert (view["status"], view["outcome"]["verdict"]) == ("defaulted", "imprison")
    assert (await api.get(f"{base}/world")).json()["status"] == "planning"


async def test_three_narration_failures_default_the_scene_to_imprisonment(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base, _, scene_id, path, headers = await _end_turn_into_judgment(api, db_connection)
    for _ in range(3):
        result = await api.post(f"{path}/failures", headers=headers)
    assert result.json()["scene_status"] == "defaulted"
    view = (await api.get(f"{base}/scenes/{scene_id}")).json()
    assert view["outcome"]["verdict"] == "imprison"


async def test_the_scene_view_carries_stances_and_the_outcome_summary(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base, _, scene_id, path, headers = await _end_turn_into_judgment(api, db_connection)
    before = (await api.get(f"{base}/scenes/{scene_id}")).json()
    assert before["outcome_summary"] == []
    assert before["participants"][0]["stance"] is None
    await api.post(f"{path}/opening", json={"text": OPENING_TEXT}, headers=headers)
    await api.post(
        f"{path}/exchanges", json=_pronouncement("execute", "publicly"), headers=headers
    )
    after = (await api.get(f"{base}/scenes/{scene_id}")).json()
    assert after["outcome_summary"][0] == "Judgment: Executed (publicly)."
    assert "Atrocities recorded: +2." in after["outcome_summary"]


async def test_the_world_view_lists_held_nobles_as_own_prisoners(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base, _, _, _, _ = await _end_turn_into_judgment(api, db_connection)
    world = (await api.get(f"{base}/world")).json()
    assert [item["id"] for item in world["own_prisoners"]] == [CAPTIVE_ID]
    assert world["own_prisoners"][0]["title"] == "Noble"
