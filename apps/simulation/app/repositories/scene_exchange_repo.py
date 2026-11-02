"""Repository for scene transcript exchanges. SQL lives only here."""

from uuid import UUID

from app.models.persistence import SceneExchangeRow
from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb
from strategy_contracts.terms import TermsCard
from strategy_contracts.treaty import Verdict, WeightBand

INSERT_EXCHANGE_SQL = """
INSERT INTO scene_exchanges (
    scene_id, sequence, player_text, leader_text, proposal, cited_grudge_ids,
    verdict, clause_bands
)
VALUES (
    %(scene_id)s, %(sequence)s, %(player_text)s, %(leader_text)s, %(proposal)s,
    %(cited_grudge_ids)s, %(verdict)s, %(clause_bands)s
)
ON CONFLICT (scene_id, sequence) DO NOTHING
RETURNING sequence
"""

SELECT_EXCHANGES_SQL = """
SELECT * FROM scene_exchanges WHERE scene_id = %(scene_id)s ORDER BY sequence
"""


async def insert_exchange(
    connection: AsyncConnection,
    scene_id: UUID,
    sequence: int,
    player_text: str,
    leader_text: str,
    proposal: TermsCard | None,
    cited_grudge_ids: list[str] | None = None,
    verdict: Verdict | None = None,
    clause_bands: list[WeightBand] | None = None,
) -> bool:
    cursor = await connection.execute(
        INSERT_EXCHANGE_SQL,
        {
            "scene_id": scene_id,
            "sequence": sequence,
            "player_text": player_text,
            "leader_text": leader_text,
            "proposal": None
            if proposal is None
            else Jsonb(proposal.model_dump(mode="json")),
            "cited_grudge_ids": cited_grudge_ids or [],
            "verdict": None if verdict is None else verdict.value,
            "clause_bands": [band.value for band in clause_bands or []],
        },
    )
    return await cursor.fetchone() is not None


async def list_exchanges(
    connection: AsyncConnection, scene_id: UUID
) -> list[SceneExchangeRow]:
    async with connection.cursor(row_factory=class_row(SceneExchangeRow)) as cursor:
        await cursor.execute(SELECT_EXCHANGES_SQL, {"scene_id": scene_id})
        return await cursor.fetchall()
