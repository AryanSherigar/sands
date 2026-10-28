"""Repository for model_answers. SQL lives only here."""

import json
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb
from strategy_contracts.scene import ModelAnswerRecord

INSERT_MODEL_ANSWER_SQL = """
INSERT INTO model_answers (playthrough_id, kind, input_hash, answer, source, turn)
VALUES (%(playthrough_id)s, %(kind)s, %(input_hash)s, %(answer)s, %(source)s, %(turn)s)
ON CONFLICT (playthrough_id, kind, input_hash) DO NOTHING
RETURNING answer_id
"""

SELECT_ANSWERS_SQL = """
SELECT input_hash, answer FROM model_answers
WHERE playthrough_id = %(playthrough_id)s AND kind NOT LIKE 'policy:%%'
ORDER BY created_at, answer_id
"""


async def record_model_answer(
    connection: AsyncConnection,
    playthrough_id: UUID,
    record: ModelAnswerRecord,
    turn: int,
) -> bool:
    cursor = await connection.execute(
        INSERT_MODEL_ANSWER_SQL,
        {
            "playthrough_id": playthrough_id,
            "kind": record.kind,
            "input_hash": record.input_hash,
            "answer": Jsonb(json.loads(record.answer_json)),
            "source": record.source,
            "turn": turn,
        },
    )
    return await cursor.fetchone() is not None


async def list_answers_by_hash(
    connection: AsyncConnection, playthrough_id: UUID
) -> dict[str, str]:
    cursor = await connection.execute(
        SELECT_ANSWERS_SQL, {"playthrough_id": playthrough_id}
    )
    rows = await cursor.fetchall()
    return {
        input_hash: json.dumps(answer, sort_keys=True, separators=(",", ":"))
        for input_hash, answer in rows
    }


def policy_answer_kind(kind: str, policy_version: str) -> str:
    return "policy:" + json.dumps([kind, policy_version], separators=(",", ":"))


async def record_policy_answer(
    connection: AsyncConnection,
    playthrough_id: UUID,
    record: ModelAnswerRecord,
    turn: int,
    policy_version: str,
) -> bool:
    namespaced = record.model_copy(
        update={"kind": policy_answer_kind(record.kind, policy_version)}
    )
    return await record_model_answer(connection, playthrough_id, namespaced, turn)


async def list_policy_answers(
    connection: AsyncConnection, playthrough_id: UUID, kind: str, policy_version: str
) -> dict[str, str]:
    query = """SELECT input_hash, answer FROM model_answers
    WHERE playthrough_id = %s AND kind = %s ORDER BY created_at, answer_id"""
    cursor = await connection.execute(
        query, (playthrough_id, policy_answer_kind(kind, policy_version))
    )
    return {
        input_hash: json.dumps(answer, sort_keys=True, separators=(",", ":"))
        for input_hash, answer in await cursor.fetchall()
    }
