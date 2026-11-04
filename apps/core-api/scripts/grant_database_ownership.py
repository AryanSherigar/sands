"""One-off: make each service role own its database.

PostgreSQL 15+ stops non-owners creating tables in the public schema, and
Cloud SQL creates every database owned by `postgres`. Run once as the admin
over the Cloud SQL socket (ADMIN_DATABASE_URL), before the migration jobs:

    python -m scripts.grant_database_ownership

Idempotent; prints the resulting owners, `max_connections` and the available
extension versions.
"""

import asyncio

import asyncpg
from app.config import settings

ADMIN_ROLE = "postgres"
DATABASE_OWNERS = {"sands_db": "core", "memory_db": "memory"}
CHECKED_EXTENSIONS = ("vector", "pg_textsearch")


def ownership_statements() -> list[str]:
    statements = [
        f"GRANT {owner} TO {ADMIN_ROLE}" for owner in DATABASE_OWNERS.values()
    ]
    statements += [
        f"ALTER DATABASE {database} OWNER TO {owner}"
        for database, owner in DATABASE_OWNERS.items()
    ]
    return statements


async def grant_ownership(connection: asyncpg.Connection) -> None:
    for statement in ownership_statements():
        await connection.execute(statement)


async def report(connection: asyncpg.Connection) -> None:
    owners = await connection.fetch(
        "SELECT datname, pg_get_userbyid(datdba) AS owner FROM pg_database "
        "WHERE datname = ANY($1)",
        list(DATABASE_OWNERS),
    )
    print("owners:", {row["datname"]: row["owner"] for row in owners})
    print("max_connections:", await connection.fetchval("SHOW max_connections"))
    extensions = await connection.fetch(
        "SELECT name, default_version FROM pg_available_extensions "
        "WHERE name = ANY($1)",
        list(CHECKED_EXTENSIONS),
    )
    print("extensions:", {row["name"]: row["default_version"] for row in extensions})


async def main() -> None:
    if not settings.admin_database_url:
        raise SystemExit("ADMIN_DATABASE_URL is not set")
    connection = await asyncpg.connect(settings.admin_database_url)
    try:
        await grant_ownership(connection)
        await report(connection)
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
