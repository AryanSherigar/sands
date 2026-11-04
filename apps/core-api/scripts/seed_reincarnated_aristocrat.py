"""Seed the "As a Reincarnated Aristocrat, I'll Use My Appraisal Skill" scenario.

Run via:
    docker exec -i sands-core-api python -m scripts.seed_reincarnated_aristocrat \
        --creator-name dambhare
    python -m scripts.seed_reincarnated_aristocrat --dry-run     # no database needed

Map images are uploaded from scripts/reincarnated_aristocrat/assets/maps/ unless
--no-maps is passed, which seeds image-less maps (the viewer lists locations).

Builds one master-mode scenario, validates it with the Core API's own validators,
replaces its rows in place as an unpublished draft owned by the named creator and
finishes by creating a playtest playthrough through PlaythroughService, so a
scenario that cannot be played fails here. The creator must be named explicitly;
there is no fallback to "any user".
"""

import argparse
import asyncio
import json
import uuid
from pathlib import Path

from app.db.connection import AsyncSessionFactory
from app.db.models.user import User
from app.models.playthrough import PlaythroughCreate, PlaythroughResponse
from scripts.reincarnated_aristocrat.builder import AppraisalScenario, build
from scripts.reincarnated_aristocrat.ids import SCENARIO_ID
from scripts.reincarnated_aristocrat.map_assets import upload_map_images
from scripts.reincarnated_aristocrat.mapart.naming import map_file_name
from scripts.reincarnated_aristocrat.persist import persist
from scripts.reincarnated_aristocrat.validation import validate
from scripts.seeding.playtest import create_playtest
from sqlalchemy import func, select


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--creator-id", type=uuid.UUID, default=None)
    group.add_argument("--creator-name", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--export", type=Path, default=None)
    parser.add_argument("--no-playtest", action="store_true")
    parser.add_argument("--no-maps", action="store_true")
    return parser.parse_args()


def summarize(built: AppraisalScenario) -> str:
    return (
        f"conditions={len(built.conditions)} entities={len(built.entities)} "
        f"endings={len(built.end_conditions)} maps={len(built.maps)} "
        f"pins={sum(len(item.pins) for item in built.maps)}"
    )


def export_payload(built: AppraisalScenario) -> dict[str, object]:
    return {
        "scenario": built.scenario,
        "conditions": [item.model_dump(mode="json") for item in built.conditions],
        "end_conditions": [
            item.model_dump(mode="json") for item in built.end_conditions
        ],
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


def describe_playtest(response: PlaythroughResponse) -> str:
    return (
        f"playtest {response.playthrough_id}: state keys={sorted(response.state)} "
        f"client snapshot keys={sorted(response.scenario_snapshot)}"
    )


async def seed(
    built: AppraisalScenario,
    creator_id: uuid.UUID | None,
    creator_name: str | None,
    should_playtest: bool,
    should_upload_maps: bool,
) -> None:
    owner = await resolve_creator(creator_id, creator_name)
    if should_upload_maps:
        await upload_map_images([map_file_name(item) for item in built.maps])
        print(f"Uploaded {len(built.maps)} map images")
    async with AsyncSessionFactory() as session, session.begin():
        await persist(session, built, owner)
    print(f"Seeded the appraisal scenario for creator {owner}")
    if not should_playtest:
        return
    async with AsyncSessionFactory() as session, session.begin():
        data = PlaythroughCreate(scenario_id=SCENARIO_ID, setup_values={})
        response = await create_playtest(session, owner, data)
    print(describe_playtest(response))


def main() -> None:
    args = parse_args()
    built = build(with_map_images=not args.no_maps)
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
    asyncio.run(
        seed(
            built,
            args.creator_id,
            args.creator_name,
            not args.no_playtest,
            not args.no_maps,
        )
    )


if __name__ == "__main__":
    main()
