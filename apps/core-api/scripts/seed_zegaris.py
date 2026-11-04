"""Seed the Zegaris "Owl's Respite" scenario.

Run via:
    docker exec -i sands-core-api python -m scripts.seed_zegaris --creator-name <name>
    python -m scripts.seed_zegaris --dry-run            # no database needed

Builds one master-mode High Fantasy scenario, validates it with the Core API's
own validators, replaces its rows in place as a private draft and finishes by
creating one playtest playthrough per outlander class through PlaythroughService,
so a scenario that cannot start fails here. The creator must be named; there is
no fallback to "any user". Making the draft visible to others is a separate
step (scripts/set_scenario_visibility.py).
"""

import argparse
import asyncio
import json
import uuid
from pathlib import Path

from app.db.connection import AsyncSessionFactory
from app.db.models.user import User
from app.models.playthrough import PlaythroughCreate, PlaythroughResponse
from scripts.zegaris.builder import ZegarisScenario, build
from scripts.zegaris.ids import SCENARIO_ID
from scripts.zegaris.map_assets import (
    has_cover_image,
    has_map_image,
    upload_cover_image,
    upload_map_image,
)
from scripts.zegaris.mechanics import CLASS_LOADOUTS
from scripts.zegaris.persist import persist
from scripts.zegaris.validation import validate
from sqlalchemy import func, select

PLAYTEST_NAME = "Alex"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--creator-id", type=uuid.UUID, default=None)
    group.add_argument("--creator-name", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--export", type=Path, default=None)
    parser.add_argument("--no-playtest", action="store_true")
    return parser.parse_args()


def summarize(built: ZegarisScenario) -> str:
    rules: dict[str, object] = built.scenario["rules"]  # type: ignore[assignment]
    encounters = rules["fantasy_combat"]["encounters"]  # type: ignore[index]
    return (
        f"conditions={len(built.conditions)} entities={len(built.entities)} "
        f"maps={len(built.maps)} pins={sum(len(item.pins) for item in built.maps)} "
        f"encounters={len(encounters)}"
    )


def export_payload(built: ZegarisScenario) -> dict[str, object]:
    return {
        "scenario": built.scenario,
        "conditions": [item.model_dump(mode="json") for item in built.conditions],
    }


async def resolve_creator(
    creator_id: uuid.UUID | None, creator_name: str | None
) -> uuid.UUID:
    if creator_id is None and creator_name is None:
        raise RuntimeError("Pass --creator-id or --creator-name; there is no default")
    async with AsyncSessionFactory() as session:
        statement = select(User.user_id)
        if creator_id is not None:
            statement = statement.where(User.user_id == creator_id)
        else:
            statement = statement.where(
                func.lower(User.display_name) == str(creator_name).lower()
            )
        found = (await session.execute(statement.limit(2))).scalars().all()
    if len(found) != 1:
        raise RuntimeError(f"Expected exactly one matching creator, found {len(found)}")
    return found[0]


def describe_playtest(class_key: str, response: PlaythroughResponse) -> str:
    return (
        f"playtest {class_key} {response.playthrough_id}: "
        f"player={response.state.get('player')}"
    )


async def playtest_every_class(owner: uuid.UUID) -> None:
    from scripts.seeding.playtest import create_playtest

    for class_key in CLASS_LOADOUTS:
        async with AsyncSessionFactory() as session, session.begin():
            data = PlaythroughCreate(
                scenario_id=SCENARIO_ID,
                setup_values={
                    "character_name": PLAYTEST_NAME,
                    "outlander_class": class_key,
                },
            )
            response = await create_playtest(session, owner, data)
        print(describe_playtest(class_key, response))


async def seed(
    built: ZegarisScenario,
    creator_id: uuid.UUID | None,
    creator_name: str | None,
    should_playtest: bool,
) -> None:
    owner = await resolve_creator(creator_id, creator_name)
    if has_map_image():
        await upload_map_image()
    if has_cover_image():
        await upload_cover_image()
    async with AsyncSessionFactory() as session, session.begin():
        await persist(session, built, owner)
    print(f"Seeded Zegaris for creator {owner}")
    if should_playtest:
        await playtest_every_class(owner)


def main() -> None:
    args = parse_args()
    built = build()
    problems = validate(built)
    print(summarize(built))
    for item in problems:
        print(f"PROBLEM: {item}")
    if problems:
        raise SystemExit(1)
    if args.export is not None:
        args.export.write_text(
            json.dumps(export_payload(built), indent=2), encoding="utf-8"
        )
    if args.dry_run:
        return
    asyncio.run(seed(built, args.creator_id, args.creator_name, not args.no_playtest))


if __name__ == "__main__":
    main()
