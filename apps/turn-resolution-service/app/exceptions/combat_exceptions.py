"""Player-facing errors for guarded combat actions."""

from app.exceptions.base import BaseAppException


class CombatActionError(BaseAppException):
    def __init__(self, message: str):
        super().__init__(
            message=message, status_code=409, error_code="combat_action_refused"
        )


class CombatReplayConflictError(BaseAppException):
    def __init__(self):
        super().__init__(
            message="The action ID was already used for a different action.",
            status_code=409,
            error_code="combat_action_conflict",
        )
