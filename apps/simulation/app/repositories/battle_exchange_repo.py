from collections.abc import Sequence
from uuid import UUID

from app.models.world_battle import ExchangeReceipt
from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

INSERT_SQL = """INSERT INTO battle_exchanges
(playthrough_id, battle_id, campaign_turn, exchange_index, total_exchange,
 input_hash, output_hash, rule_version, receipt)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
LIST_SQL = """SELECT receipt FROM battle_exchanges
WHERE playthrough_id = %s AND battle_id = %s
AND total_exchange > %s ORDER BY total_exchange LIMIT %s"""
LIST_FOR_TURN_SQL = """SELECT receipt FROM battle_exchanges
WHERE playthrough_id = %s AND campaign_turn = %s
ORDER BY battle_id, total_exchange"""


async def append_exchanges(
    connection: AsyncConnection,
    playthrough_id: UUID,
    receipts: Sequence[ExchangeReceipt],
) -> None:
    async with connection.cursor() as cursor:
        await cursor.executemany(
            INSERT_SQL,
            [
                (
                    playthrough_id,
                    receipt.battle_id,
                    receipt.campaign_turn,
                    receipt.exchange_index,
                    receipt.total_exchange,
                    receipt.input_hash,
                    receipt.output_hash,
                    receipt.rule_version,
                    Jsonb(receipt.model_dump(mode="json")),
                )
                for receipt in receipts
            ],
        )


async def list_exchanges(
    connection: AsyncConnection,
    playthrough_id: UUID,
    battle_id: str,
    limit: int = 100,
    after_exchange: int = 0,
) -> list[ExchangeReceipt]:
    cursor = await connection.execute(
        LIST_SQL, (playthrough_id, battle_id, after_exchange, min(max(limit, 1), 201))
    )
    return [ExchangeReceipt.model_validate(row[0]) for row in await cursor.fetchall()]


async def list_exchanges_for_turn(
    connection: AsyncConnection, playthrough_id: UUID, campaign_turn: int
) -> list[ExchangeReceipt]:
    cursor = await connection.execute(
        LIST_FOR_TURN_SQL, (playthrough_id, campaign_turn)
    )
    return [ExchangeReceipt.model_validate(row[0]) for row in await cursor.fetchall()]
