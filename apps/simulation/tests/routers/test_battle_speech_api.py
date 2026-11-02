from httpx import AsyncClient
from psycopg import AsyncConnection
from tests.engine.battles.test_battle_speech_state import take_command
from tests.services.helpers import mutation, seed_world

SPEECH_WAVE = 1


async def _seeded_base(db_connection: AsyncConnection, speech_ruleset: int = 1) -> str:
    world, scenario = take_command(speech_ruleset=speech_ruleset)
    identity = await seed_world(db_connection, world, scenario)
    return f"/v1/playthroughs/{identity}"


def _talk(name: str, version: int, index: int, text: str = "Stand with me.") -> dict:
    guard = mutation(name, version, turn=0, wave=SPEECH_WAVE).model_dump()
    return {"guard": guard, "talk_index": index, "text": text}


async def test_the_view_reports_a_pending_speech_with_an_informal_report(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seeded_base(db_connection)
    response = await api.get(f"{base}/battles/battle_1/speech")
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["status"], body["next_talk"], body["reactions"]) == ("pending", 1, [])
    assert body["officer_report"]
    assert not any(character.isdigit() for character in body["officer_report"])
    assert set(body["mood"]) == {"morale", "exhaustion", "pay"}


async def test_the_battle_view_exposes_the_pending_speech(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seeded_base(db_connection)
    battle = (await api.get(f"{base}/battles/battle_1")).json()
    assert battle["speech_status"] == "pending"


async def test_waves_are_blocked_until_the_speech_is_done(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seeded_base(db_connection)
    guard = mutation("blocked", 1, turn=0, wave=SPEECH_WAVE).model_dump()
    response = await api.post(f"{base}/battles/advance", json=guard)
    assert response.status_code == 409


async def test_three_talks_then_the_battle_runs_and_replay_verifies(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seeded_base(db_connection)
    version = 1
    for index in (1, 2, 3):
        response = await api.post(
            f"{base}/battles/battle_1/speech/talks",
            json=_talk(f"talk{index}", version, index),
        )
        assert response.status_code == 200, response.text
        version = response.json()["state"]["world_version"]
    assert response.json()["is_complete"] is True
    assert response.json()["morale_delta_percent"] == 0
    for wave in range(1, 5):
        advanced = await api.post(
            f"{base}/battles/advance",
            json=mutation(f"wave{wave}", version, wave=wave).model_dump(),
        )
        assert advanced.status_code == 200, advanced.text
        version = advanced.json()["world_version"]
    verified = await api.post(f"{base}/replay/verify?through_turn=1")
    assert verified.status_code == 200, verified.text


async def test_blank_text_is_rejected(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seeded_base(db_connection)
    response = await api.post(
        f"{base}/battles/battle_1/speech/talks", json=_talk("blank", 1, 1, "   ")
    )
    assert response.status_code == 422


async def test_an_out_of_order_talk_is_a_conflict(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seeded_base(db_connection)
    response = await api.post(
        f"{base}/battles/battle_1/speech/talks", json=_talk("early", 1, 2)
    )
    assert response.status_code == 409


async def test_retrying_a_talk_returns_the_same_response(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seeded_base(db_connection)
    body = _talk("retry", 1, 1)
    first = await api.post(f"{base}/battles/battle_1/speech/talks", json=body)
    second = await api.post(f"{base}/battles/battle_1/speech/talks", json=body)
    assert first.status_code == second.status_code == 200
    assert second.json()["state"] == first.json()["state"]


async def test_skipping_ends_the_speech_and_unblocks_the_waves(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seeded_base(db_connection)
    guard = mutation("skip", 1, turn=0, wave=SPEECH_WAVE).model_dump()
    skipped = await api.post(f"{base}/battles/battle_1/speech/skip", json=guard)
    assert skipped.status_code == 200, skipped.text
    assert skipped.json()["is_complete"] is True
    version = skipped.json()["state"]["world_version"]
    advanced = await api.post(
        f"{base}/battles/advance",
        json=mutation("wave1", version, wave=1).model_dump(),
    )
    assert advanced.status_code == 200, advanced.text


async def test_a_battle_without_a_speech_is_not_found(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    base = await _seeded_base(db_connection, speech_ruleset=0)
    assert (await api.get(f"{base}/battles/battle_1/speech")).status_code == 404
    assert (await api.get(f"{base}/battles/nobody/speech")).status_code == 404
