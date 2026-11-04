"""Make a scenario private or public, and manage who may open a private one.

A private scenario is open to its creator and the users on its allowlist, and to
no one else. The creator never needs to be on the list. Playthroughs already
started keep the visibility they were created with. Safe to run twice.

Usage:
    python -m scripts.set_scenario_visibility --scenario-id UUID \
        [--visibility private|public] [--allow UUID ...] [--revoke UUID ...]
"""

import argparse
import asyncio
import sys
import uuid
from dataclasses import dataclass

from app.db.connection import close_db_connection, get_session_factory
from app.exceptions.base import BaseAppException
from app.repositories.scenario_access_repo import ScenarioAccessRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.user_repo import UserRepo
from app.services.scenario_visibility_service import (
    VISIBILITIES,
    ScenarioVisibilityService,
)
from sqlalchemy.ext.asyncio import AsyncSession

EXIT_OK = 0
EXIT_FAILED = 1


@dataclass(frozen=True)
class CommandResult:
    output: str
    exit_code: int = EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Set a scenario's visibility.")
    parser.add_argument("--scenario-id", type=uuid.UUID, required=True)
    parser.add_argument("--visibility", choices=VISIBILITIES, default=None)
    parser.add_argument("--allow", type=uuid.UUID, action="append", default=[])
    parser.add_argument("--revoke", type=uuid.UUID, action="append", default=[])
    return parser


def _build_service(session: AsyncSession) -> ScenarioVisibilityService:
    return ScenarioVisibilityService(
        ScenarioRepo(session), ScenarioAccessRepo(session), UserRepo(session)
    )


async def _apply(args: argparse.Namespace, service: ScenarioVisibilityService) -> None:
    if args.visibility is not None:
        await service.set_visibility(args.scenario_id, args.visibility)
    for user_id in args.allow:
        await service.allow(args.scenario_id, user_id)
    for user_id in args.revoke:
        await service.revoke(args.scenario_id, user_id)


async def run_command(args: argparse.Namespace, session: AsyncSession) -> CommandResult:
    service = _build_service(session)
    try:
        await _apply(args, service)
        allowed = await service.allowed_user_ids(args.scenario_id)
        scenario = await service.scenario_repo.get_by_id(args.scenario_id)
    except BaseAppException as error:
        return CommandResult(f"Failed: {error.message}", EXIT_FAILED)
    names = ", ".join(str(user_id) for user_id in allowed) or "none (creator only)"
    return CommandResult(
        f"{scenario.scenario_id} ({scenario.title}): {scenario.visibility}; "
        f"also allowed: {names}"
    )


async def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        async with get_session_factory()() as session:
            result = await run_command(args, session)
            await session.commit()
    finally:
        await close_db_connection()
    sys.stdout.write(f"{result.output}\n")
    return result.exit_code


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
