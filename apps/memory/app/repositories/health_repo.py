"""Database health checks. The only file that queries Postgres for GET /health."""

from psycopg import AsyncConnection

REQUIRED_EXTENSION_NAMES: tuple[str, ...] = ("vector", "pg_textsearch")

CHECK_DATABASE_SQL = "SELECT 1"

GET_INSTALLED_EXTENSIONS_SQL = (
    "SELECT extname FROM pg_extension WHERE extname = ANY(%s)"
)


async def is_database_reachable(connection: AsyncConnection) -> bool:
    async with connection.cursor() as cursor:
        await cursor.execute(CHECK_DATABASE_SQL)
        row = await cursor.fetchone()
    return row is not None and row[0] == 1


async def get_installed_extensions(connection: AsyncConnection) -> set[str]:
    async with connection.cursor() as cursor:
        await cursor.execute(
            GET_INSTALLED_EXTENSIONS_SQL, (list(REQUIRED_EXTENSION_NAMES),)
        )
        rows = await cursor.fetchall()
    return {row[0] for row in rows}
