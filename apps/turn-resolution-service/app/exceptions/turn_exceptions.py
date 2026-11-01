"""Turn pipeline domain exception classes."""

from app.exceptions.base import BaseAppException


class PlaythroughNotActiveError(BaseAppException):
    """Raised when a turn is submitted against a missing or non-active playthrough."""

    def __init__(self, message: str = "Playthrough is not active"):
        super().__init__(message=message, status_code=409)


class StrategyTurnUnsupportedError(BaseAppException):
    """Raised when a strategy campaign is submitted to the narrative pipeline."""

    def __init__(self, message: str = "Strategy turns are resolved by Simulation"):
        super().__init__(
            message=message, status_code=409, error_code="strategy_turn_unsupported"
        )


class ParticipantNotFoundError(BaseAppException):
    """Raised when the acting participant doesn't belong to the playthrough."""

    def __init__(self, message: str = "Participant not found"):
        super().__init__(message=message, status_code=404)


class ParticipantAccessDeniedError(BaseAppException):
    """Raised when the acting participant does not belong to the authenticated user."""

    def __init__(
        self, message: str = "Participant does not belong to authenticated user"
    ):
        super().__init__(message=message, status_code=403)


class TurnOrderError(BaseAppException):
    """Raised when a participant acts out of turn in a multiplayer playthrough."""

    def __init__(self, message: str = "It is not this participant's turn"):
        super().__init__(message=message, status_code=409)


class LlmUnavailableError(BaseAppException):
    """Raised when Gemini is transiently unavailable (timeout, 5xx, rate limit)."""

    def __init__(self, message: str = "Narrator is temporarily unavailable"):
        super().__init__(message=message, status_code=502)


class LlmContentBlockedError(BaseAppException):
    """Raised when Gemini rejects a request outright (safety filter, permission
    denial) rather than being transiently unavailable — retrying will not help."""

    def __init__(self, message: str = "Narrator declined to process this request"):
        super().__init__(message=message, status_code=400)


class LlmNotConfiguredError(BaseAppException):
    """Raised when the narrator provider cannot authenticate or reach its model
    (missing ADC, model not enabled for the project) — retrying will not help."""

    def __init__(self, message: str = "Narrator is not configured"):
        super().__init__(message=message, status_code=503)


class NarrationGenerationError(BaseAppException):
    """Raised when Gemini narration generation fails after retries."""

    def __init__(self, message: str = "Narration generation failed"):
        super().__init__(message=message, status_code=502)


class StateWriteError(BaseAppException):
    """Raised when persisting turn state fails after retries."""

    def __init__(self, message: str = "Failed to persist turn state"):
        super().__init__(message=message, status_code=500)


class MinigameResultRequiredError(BaseAppException):
    """Raised when a normal action is submitted while a minigame is pending
    resolution — a playthrough can never silently drop a pending minigame."""

    def __init__(
        self,
        message: str = "A minigame result must be submitted before any other action",
    ):
        super().__init__(message=message, status_code=409)


class MinigameResultMismatchError(BaseAppException):
    """Raised when a submitted minigame result doesn't match the pending
    minigame, or when none is pending at all."""

    def __init__(
        self,
        message: str = "Submitted minigame result does not match the pending minigame",
    ):
        super().__init__(message=message, status_code=409)


class CheckResolutionRequiredError(BaseAppException):
    """Raised when a normal action is submitted while a check is pending
    resolution — a playthrough can never silently drop a pending check."""

    def __init__(
        self,
        message: str = "A check must be resolved (attempt or decline) before any other action",
    ):
        super().__init__(message=message, status_code=409)


class CheckResolutionMismatchError(BaseAppException):
    """Raised when a submitted check resolution doesn't match the pending
    check, or when none is pending at all."""

    def __init__(
        self,
        message: str = "Submitted check resolution does not match the pending check",
    ):
        super().__init__(message=message, status_code=409)


class CheckOwnershipError(BaseAppException):
    """Raised when a participant other than the one who proposed the check
    tries to resolve it — check resolution bypasses normal turn-order
    rotation but is restricted to the check's owner."""

    def __init__(
        self,
        message: str = "Only the participant who proposed this check may resolve it",
    ):
        super().__init__(message=message, status_code=403)


class OptimisticLockError(BaseAppException):
    """Raised when a concurrent write updated the playthrough state first."""

    def __init__(
        self, message: str = "Playthrough state was modified by another transaction"
    ):
        super().__init__(message=message, status_code=409)


class SceneImageGenerationError(BaseAppException):
    """Raised when scene image generation or upload fails.

    Caught and swallowed inside scene_image_generator.py — a missing scene
    image must never fail or degrade a turn — but the exception type is
    still domain-specific per CLAUDE.md's error handling rules.
    """

    def __init__(self, message: str = "Scene image generation failed"):
        super().__init__(message=message, status_code=502)


class CheckReportInvalidError(BaseAppException):
    """Raised when a rule-check report names no option of the pending check, or
    neither names one nor says the timer ran out."""

    def __init__(self, message: str = "Rule check report does not name a valid option"):
        super().__init__(message=message, status_code=422)


class CheckNotArmedError(BaseAppException):
    """Raised when a rule-check report arrives before the prompt's clock was
    started by arming it."""

    def __init__(self, message: str = "Rule check has not been armed yet"):
        super().__init__(message=message, status_code=409)
