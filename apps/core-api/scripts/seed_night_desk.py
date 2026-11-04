"""Seed the "Night Desk, Floor 9" rules-horror scenario.

Run via:
    docker exec -i sands-core-api python -m scripts.seed_night_desk
    python -m scripts.seed_night_desk --dry-run            # no database needed

Builds one scenario with all five tools enabled, validates it with the Core API's
own validators, replaces its rows in place and finishes by creating a playtest
playthrough through PlaythroughService, so a scenario that cannot be played fails
here (docs/specs/rules-horror-engine/night-desk-generator-v2.spec.md).
"""

import argparse
import asyncio
import json
import uuid
from pathlib import Path

from app.db.connection import AsyncSessionFactory
from app.db.models.user import User
from app.models.playthrough import PlaythroughCreate, PlaythroughResponse
from scripts.night_desk import timeline
from scripts.night_desk.builder import NightDeskScenario, build
from scripts.night_desk.cover import upload_cover
from scripts.night_desk.ids import SCENARIO_ID
from scripts.night_desk.music import upload_tier_tracks
from scripts.night_desk.persist import persist
from scripts.night_desk.playtest import create_playtest
from scripts.night_desk.poster import poster_url, upload_poster
from scripts.night_desk.validation import validate
from sqlalchemy import select

PLAYTEST_NAME = "Alex"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--creator-id", type=uuid.UUID, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--export", type=Path, default=None)
    parser.add_argument("--no-playtest", action="store_true")
    parser.add_argument("--no-music", action="store_true")
    parser.add_argument("--no-cover", action="store_true")
    parser.add_argument("--no-poster", action="store_true")
    return parser.parse_args()


def summarize(built: NightDeskScenario) -> str:
    return (
        f"turns={timeline.EXPECTED_TURN_COUNT} conditions={len(built.conditions)} entities={len(built.entities)} "
        f"facts={len(built.facts)} endings={len(built.end_conditions)} "
        f"invariants={len(built.invariants)} minigames={len(built.minigames)} "
        f"rule_checks={len(built.rule_checks)} sheet_rules={len(built.sheet_rules)}"
    )


def export_payload(built: NightDeskScenario) -> dict[str, object]:
    return {
        "scenario": built.scenario,
        "conditions": [item.model_dump(mode="json") for item in built.conditions],
        "end_conditions": [
            item.model_dump(mode="json") for item in built.end_conditions
        ],
        "invariants": [item.model_dump(mode="json") for item in built.invariants],
        "minigames": [item.model_dump(mode="json") for item in built.minigames],
        "rule_checks": [item.model_dump(mode="json") for item in built.rule_checks],
        "sheet_rules": [item.model_dump(mode="json") for item in built.sheet_rules],
    }


def export_json(built: NightDeskScenario, path: Path) -> None:
    path.write_text(json.dumps(export_payload(built), indent=2), encoding="utf-8")


async def resolve_creator(creator_id: uuid.UUID | None) -> uuid.UUID:
    async with AsyncSessionFactory() as session:
        statement = select(User.user_id)
        if creator_id is not None:
            statement = statement.where(User.user_id == creator_id)
        found = (await session.execute(statement.limit(1))).scalar_one_or_none()
    if found is None:
        raise RuntimeError("No matching user found to act as the scenario creator")
    return found


def describe_playtest(response: PlaythroughResponse) -> str:
    return (
        f"playtest {response.playthrough_id}: state keys={sorted(response.state)} "
        f"client snapshot keys={sorted(response.scenario_snapshot)} "
        f"rule sheet={len(response.rule_sheet)} rules"
    )


async def upload_checked_poster() -> None:
    url = await upload_poster()
    if url != poster_url():
        raise RuntimeError(
            f"Poster uploaded to {url}, conditions point at {poster_url()}"
        )
    print("Uploaded lobby poster")


async def seed(
    built: NightDeskScenario,
    creator_id: uuid.UUID | None,
    should_playtest: bool,
    should_upload_music: bool,
    should_upload_cover: bool,
    should_upload_poster: bool,
) -> None:
    owner = await resolve_creator(creator_id)
    if should_upload_cover:
        built.scenario["cover_image_url"] = await upload_cover()
        print("Uploaded cover image")
    if should_upload_poster:
        await upload_checked_poster()
    if should_upload_music:
        urls = await upload_tier_tracks()
        print(f"Uploaded {len(urls)} tier tracks")
    async with AsyncSessionFactory() as session, session.begin():
        await persist(session, built, owner)
    print(f"Seeded Night Desk for creator {owner}")
    if not should_playtest:
        return
    async with AsyncSessionFactory() as session, session.begin():
        data = PlaythroughCreate(
            scenario_id=SCENARIO_ID, setup_values={"character_name": PLAYTEST_NAME}
        )
        response = await create_playtest(session, owner, data)
    print(describe_playtest(response))


def main() -> None:
    args = parse_args()
    built = build()
    problems = validate(built)
    print(summarize(built))
    for problem in problems:
        print(f"PROBLEM: {problem}")
    if problems:
        raise SystemExit(1)
    if args.export:
        export_json(built, args.export)
    if not args.dry_run:
        asyncio.run(
            seed(
                built,
                args.creator_id,
                not args.no_playtest,
                not args.no_music,
                not args.no_cover,
                not args.no_poster,
            )
        )


if __name__ == "__main__":
    main()
