import json

import pytest
from app.repositories import model_answer_repo
from psycopg import AsyncConnection
from strategy_contracts.scene import ModelAnswerRecord

from tests.models.builders import PLAYTHROUGH_ID
from tests.repositories.helpers import seed_playthrough


def _record(kind: str, input_hash: str, answer: dict[str, object], source="live"):
    return ModelAnswerRecord(
        kind=kind,
        input_hash=input_hash,
        answer_json=json.dumps(answer),
        source=source,
    )


async def test_first_answer_is_kept(db_connection) -> None:
    await seed_playthrough(db_connection)
    first = await model_answer_repo.record_model_answer(
        db_connection, PLAYTHROUGH_ID, _record("stance", "h1", {"pick": "expand"}), 2
    )
    second = await model_answer_repo.record_model_answer(
        db_connection,
        PLAYTHROUGH_ID,
        _record("stance", "h1", {"pick": "rebuild"}, "default"),
        2,
    )
    answers = await model_answer_repo.list_answers_by_hash(
        db_connection, PLAYTHROUGH_ID
    )
    assert (first, second) == (True, False)
    assert json.loads(answers["h1"]) == {"pick": "expand"}


async def test_different_hashes_both_list(db_connection) -> None:
    await seed_playthrough(db_connection)
    for input_hash in ("h1", "h2"):
        await model_answer_repo.record_model_answer(
            db_connection, PLAYTHROUGH_ID, _record("grade", input_hash, {"tone": 3}), 1
        )
    answers = await model_answer_repo.list_answers_by_hash(
        db_connection, PLAYTHROUGH_ID
    )
    assert set(answers) == {"h1", "h2"}


async def test_no_answers_is_an_empty_mapping(db_connection) -> None:
    await seed_playthrough(db_connection)
    assert (
        await model_answer_repo.list_answers_by_hash(db_connection, PLAYTHROUGH_ID)
        == {}
    )


async def test_answer_json_comes_back_canonical(db_connection) -> None:
    await seed_playthrough(db_connection)
    record = ModelAnswerRecord(
        kind="grade",
        input_hash="h1",
        answer_json='{ "b": 1,  "a": 2 }',
        source="live",
    )
    await model_answer_repo.record_model_answer(
        db_connection, PLAYTHROUGH_ID, record, 1
    )
    answers = await model_answer_repo.list_answers_by_hash(
        db_connection, PLAYTHROUGH_ID
    )
    assert answers["h1"] == '{"a":2,"b":1}'


async def test_invalid_answer_json_is_refused(db_connection) -> None:
    await seed_playthrough(db_connection)
    record = ModelAnswerRecord(
        kind="grade", input_hash="h1", answer_json="not json", source="live"
    )
    with pytest.raises(ValueError):
        await model_answer_repo.record_model_answer(
            db_connection, PLAYTHROUGH_ID, record, 1
        )


async def test_policy_answers_are_namespaced_by_kind_and_version(
    db_connection: AsyncConnection,
) -> None:
    await seed_playthrough(db_connection)
    for kind, policy, pick in [
        ("battle_intent", "v1", "press"),
        ("battle_intent", "v2", "delay"),
        ("stance", "v1", "preserve"),
    ]:
        await model_answer_repo.record_policy_answer(
            db_connection,
            PLAYTHROUGH_ID,
            _record(kind, "same-hash", {"pick": pick}),
            0,
            policy,
        )
    answers = await model_answer_repo.list_policy_answers(
        db_connection, PLAYTHROUGH_ID, "battle_intent", "v1"
    )
    assert answers == {"same-hash": '{"pick":"press"}'}
