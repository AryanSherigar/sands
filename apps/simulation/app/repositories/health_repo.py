"""Database health check. The only file that queries Postgres for GET /health."""

from psycopg import AsyncConnection

CHECK_DATABASE_SQL = "SELECT 1"


async def is_database_reachable(connection: AsyncConnection) -> bool:
    async with connection.cursor() as cursor:
        await cursor.execute(CHECK_DATABASE_SQL)
        row = await cursor.fetchone()
    return row is not None and row[0] == 1
