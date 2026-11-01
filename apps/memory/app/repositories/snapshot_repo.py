"""Transaction-level settings shared by read-only request handlers."""

from psycopg import AsyncConnection

BEGIN_READ_ONLY_SNAPSHOT_SQL = (
    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
)


async def begin_read_only_snapshot(connection: AsyncConnection) -> None:
    """Must be the first statement of the transaction: every later read then sees
    one consistent snapshot and any write is rejected."""
    await connection.execute(BEGIN_READ_ONLY_SNAPSHOT_SQL)
