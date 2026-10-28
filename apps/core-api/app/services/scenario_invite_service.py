"""Single-use invite links and the allowlist of a private scenario."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from app.config import settings
from app.db.models.scenario import Scenario
from app.db.models.scenario_invite import ScenarioInvite
from app.exceptions.scenario_exceptions import InviteInvalidError, ScenarioNotFoundError
from app.logging_config import log_audit_event
from app.models.scenario_access import (
    ScenarioAccessMember,
    ScenarioInviteAcceptResponse,
    ScenarioInviteResponse,
)
from app.repositories.scenario_access_repo import ScenarioAccessRepo
from app.repositories.scenario_invite_repo import ScenarioInviteRepo
from app.repositories.scenario_repo import ScenarioRepo

logger = structlog.get_logger()

EVENT_SCENARIO_INVITE_CREATED = "scenario_invite_created"
EVENT_SCENARIO_INVITE_ACCEPTED = "scenario_invite_accepted"
EVENT_SCENARIO_ACCESS_REVOKED = "scenario_access_revoked"
INVITE_TOKEN_BYTES = 32
INVITE_USED_MESSAGE = "This invite has already been used or has expired"
HTTP_GONE = 410


def hash_invite_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class ScenarioInviteService:
    def __init__(
        self,
        invite_repo: ScenarioInviteRepo,
        access_repo: ScenarioAccessRepo,
        scenario_repo: ScenarioRepo,
    ) -> None:
        self.invite_repo = invite_repo
        self.access_repo = access_repo
        self.scenario_repo = scenario_repo

    async def create_invite(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID
    ) -> ScenarioInviteResponse:
        """Mint a single-use link; only its hash is kept."""
        await self._get_owned_scenario(scenario_id, user_id)
        token = secrets.token_urlsafe(INVITE_TOKEN_BYTES)
        expires_at = datetime.now(UTC) + timedelta(
            days=settings.scenario_invite_ttl_days
        )
        await self.invite_repo.create(
            ScenarioInvite(
                scenario_id=scenario_id,
                created_by=user_id,
                token_hash=hash_invite_token(token),
                expires_at=expires_at,
            )
        )
        log_audit_event(
            logger, EVENT_SCENARIO_INVITE_CREATED, scenario_id=str(scenario_id)
        )
        return ScenarioInviteResponse(
            url=f"{settings.frontend_base_url}/invite/{token}", expires_at=expires_at
        )

    async def accept_invite(
        self, token: str, user_id: uuid.UUID
    ) -> ScenarioInviteAcceptResponse:
        """Add the taker to the allowlist and burn the token. The creator opening
        their own link gets in without spending it."""
        token_hash = hash_invite_token(token)
        invite = await self.invite_repo.get_by_token_hash(token_hash)
        if invite is None:
            raise InviteInvalidError()
        scenario = await self.scenario_repo.get_by_id(invite.scenario_id)
        if scenario is None or scenario.status == "archived":
            raise InviteInvalidError()
        if scenario.creator_id != user_id:
            await self._burn_and_allow(token_hash, scenario, user_id)
        return ScenarioInviteAcceptResponse(scenario_id=scenario.scenario_id)

    async def list_members(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[ScenarioAccessMember]:
        await self._get_owned_scenario(scenario_id, user_id)
        members = await self.access_repo.list_members(scenario_id)
        return [
            ScenarioAccessMember(user_id=member_id, display_name=display_name)
            for member_id, display_name in members
        ]

    async def remove_member(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID, member_id: uuid.UUID
    ) -> None:
        await self._get_owned_scenario(scenario_id, user_id)
        await self.access_repo.remove(scenario_id, member_id)
        log_audit_event(
            logger, EVENT_SCENARIO_ACCESS_REVOKED, scenario_id=str(scenario_id)
        )

    async def _burn_and_allow(
        self, token_hash: str, scenario: Scenario, user_id: uuid.UUID
    ) -> None:
        is_consumed = await self.invite_repo.consume(
            token_hash, user_id, datetime.now(UTC)
        )
        if not is_consumed:
            raise InviteInvalidError(INVITE_USED_MESSAGE, status_code=HTTP_GONE)
        await self.access_repo.add(scenario.scenario_id, user_id)
        log_audit_event(
            logger,
            EVENT_SCENARIO_INVITE_ACCEPTED,
            scenario_id=str(scenario.scenario_id),
        )

    async def _get_owned_scenario(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID
    ) -> Scenario:
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        is_owner = scenario is not None and scenario.creator_id == user_id
        if scenario is None or scenario.status == "archived" or not is_owner:
            raise ScenarioNotFoundError()
        return scenario
