"""Starts the clock of a rule check once the player has had the chance to read
the narration that set it up.

The prompt is stamped unarmed when the turn is built, so reading time never
counts against the window. Arming is idempotent: only the first call stamps
`issued_at`, so a reload cannot buy extra time.
"""

import structlog
from app.exceptions.turn_exceptions import (
    CheckResolutionMismatchError,
    ParticipantAccessDeniedError,
    ParticipantNotFoundError,
    PlaythroughNotActiveError,
)
from app.models.auth import CurrentUser
from app.models.check_event import RuleCheckArmedPayload, RuleCheckArmInput
from app.repositories.participant_repo import ParticipantRepo
from app.repositories.playthrough_repo import PlaythroughRepo
from app.turn.rule_check_report import current_time_ms, is_armed
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

EVENT_RULE_CHECK_ARMED = "rule_check_armed"
STATE_KEY_PENDING_CHECK = "_pending_check"
STATUS_ACTIVE = "active"


async def arm_rule_check(
    arm_input: RuleCheckArmInput,
    current_user: CurrentUser,
    session: AsyncSession,
) -> RuleCheckArmedPayload:
    playthrough_repo = PlaythroughRepo(session)
    await _validate_participant(arm_input, current_user, ParticipantRepo(session))
    playthrough = await playthrough_repo.get_by_id_for_update(arm_input.playthrough_id)
    if playthrough is None or playthrough.status != STATUS_ACTIVE:
        raise PlaythroughNotActiveError()
    state = playthrough.state if isinstance(playthrough.state, dict) else {}
    pending = state.get(STATE_KEY_PENDING_CHECK)
    if not isinstance(pending, dict) or pending.get("check_id") != arm_input.check_id:
        raise CheckResolutionMismatchError()
    if not is_armed(pending):
        pending = {**pending, "is_armed": True, "issued_at": current_time_ms()}
        await playthrough_repo.update_state(
            arm_input.playthrough_id,
            {**state, STATE_KEY_PENDING_CHECK: pending},
            new_turn_count=playthrough.turn_count,
            expected_turn_count=playthrough.turn_count,
        )
        logger.info(EVENT_RULE_CHECK_ARMED, check_id=arm_input.check_id)
    await playthrough_repo.session.commit()
    return _armed_payload(arm_input.check_id, pending)


async def _validate_participant(
    arm_input: RuleCheckArmInput,
    current_user: CurrentUser,
    participant_repo: ParticipantRepo,
) -> None:
    participant = await participant_repo.get_by_id(arm_input.participant_id)
    if participant is None or participant.playthrough_id != arm_input.playthrough_id:
        raise ParticipantNotFoundError()
    if participant.user_id != current_user.user_id:
        raise ParticipantAccessDeniedError()


def _armed_payload(check_id: str, pending: dict[str, object]) -> RuleCheckArmedPayload:
    issued_at, window_ms = pending.get("issued_at"), pending.get("window_ms")
    return RuleCheckArmedPayload(
        check_id=check_id,
        issued_at=issued_at if isinstance(issued_at, int) else 0,
        window_ms=window_ms if isinstance(window_ms, int) else 0,
        server_time_ms=current_time_ms(),
    )
