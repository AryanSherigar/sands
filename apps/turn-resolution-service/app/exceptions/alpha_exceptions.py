"""Alpha-mode domain exception classes."""

from app.exceptions.base import BaseAppException

ALPHA_FEATURE_DISABLED_CODE = "alpha_feature_disabled"
ALPHA_SCENARIO_ONLY_CODE = "alpha_scenario_only"
ALPHA_PAUSED_CODE = "alpha_paused"


class AlphaFeatureDisabledError(BaseAppException):
    """Raised when a locked feature is used while alpha mode is on."""

    def __init__(self, message: str = "This feature is disabled during the alpha"):
        super().__init__(
            message=message, status_code=403, error_code=ALPHA_FEATURE_DISABLED_CODE
        )


class AlphaScenarioOnlyError(BaseAppException):
    """Raised when a non-alpha scenario is played while alpha mode is on."""

    def __init__(self, message: str = "Only the alpha scenario can be played"):
        super().__init__(
            message=message, status_code=403, error_code=ALPHA_SCENARIO_ONLY_CODE
        )


class AlphaPausedError(BaseAppException):
    """Raised when the owner has paused every turn during the alpha."""

    def __init__(self, message: str = "The night desk is closed. Try again later."):
        super().__init__(message=message, status_code=503, error_code=ALPHA_PAUSED_CODE)
