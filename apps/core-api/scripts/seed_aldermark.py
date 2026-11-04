"""Seed "The Aldermark" strategy showcase scenario.

Run via:
    python -m scripts.seed_aldermark --creator-id <uuid>
    python -m scripts.seed_aldermark --dry-run            # no database or storage

Validates the traced strategy document with the same publish checks the Core API
runs, uploads the painted map, and replaces the scenario row in place as a draft
owned by the named creator. There is no fallback to "any user". Publishing is a
separate step (scripts/publish_scenario.py).
"""

import argparse
import asyncio
import uuid

from app.db.connection import AsyncSessionFactory
from app.db.models.user import User
from scripts.aldermark.builder import TITLE, scenario_columns
from scripts.aldermark.ids import SCENARIO_ID
from scripts.aldermark.map_assets import has_map_image, upload_map_image
from scripts.aldermark.persist import persist
from sqlalchemy import select

DRY_RUN_MAP_URL = "https://example.invalid/aldermark/map.webp"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--creator-id", type=uuid.UUID, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


async def resolve_creator(creator_id: uuid.UUID | None) -> uuid.UUID:
    if creator_id is None:
        raise RuntimeError("Pass --creator-id; there is no default")
    async with AsyncSessionFactory() as session:
        statement = select(User.user_id).where(User.user_id == creator_id)
        found = (await session.execute(statement.limit(2))).scalars().all()
    if len(found) != 1:
        raise RuntimeError(f"Expected exactly one matching creator, found {len(found)}")
    return found[0]


async def seed(creator_id: uuid.UUID | None) -> None:
    if not has_map_image():
        raise RuntimeError("The Aldermark map asset is missing")
    owner = await resolve_creator(creator_id)
    columns = scenario_columns(await upload_map_image())
    async with AsyncSessionFactory() as session, session.begin():
        await persist(session, columns, owner)
    print(f"Seeded {TITLE} ({SCENARIO_ID}) for creator {owner}")


def main() -> None:
    args = parse_args()
    columns = scenario_columns(DRY_RUN_MAP_URL)
    print(f"{TITLE}: strategy document valid, {len(columns)} scenario columns")
    if args.dry_run:
        return
    asyncio.run(seed(args.creator_id))


if __name__ == "__main__":
    main()
