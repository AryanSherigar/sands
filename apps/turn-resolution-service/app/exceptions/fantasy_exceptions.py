from app.exceptions.base import BaseAppException


class FantasyActionError(BaseAppException):
    """An authored fantasy action is invalid in the current state."""

    def __init__(self, message: str):
        super().__init__(
            message=message, status_code=409, error_code="fantasy_action_refused"
        )


class FantasyReplayConflictError(BaseAppException):
    def __init__(self):
        super().__init__(
            message="The action ID was already used for a different action.",
            status_code=409,
        )
