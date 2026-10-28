"""Alpha-mode domain exception classes."""

from app.exceptions.base import BaseAppException

ALPHA_SIGNUP_CLOSED_CODE = "alpha_signup_closed"
ALPHA_CONSENT_REQUIRED_CODE = "alpha_consent_required"
ALPHA_INVITE_REQUIRED_CODE = "alpha_invite_required"
ALPHA_INVITE_INVALID_CODE = "alpha_invite_invalid"
ALPHA_FEATURE_DISABLED_CODE = "alpha_feature_disabled"
ALPHA_SCENARIO_ONLY_CODE = "alpha_scenario_only"
ALPHA_SURVEY_ALREADY_SUBMITTED_CODE = "alpha_survey_already_submitted"
ACCOUNT_SUSPENDED_CODE = "account_suspended"


class AlphaSignupClosedError(BaseAppException):
    """Raised when sign-up is switched off during the alpha."""

    def __init__(self, message: str = "Sign-up is currently closed"):
        super().__init__(
            message=message, status_code=403, error_code=ALPHA_SIGNUP_CLOSED_CODE
        )


class AlphaConsentRequiredError(BaseAppException):
    """Raised when the current alpha consent version has not been accepted."""

    def __init__(self, message: str = "Alpha consent is required"):
        super().__init__(
            message=message, status_code=403, error_code=ALPHA_CONSENT_REQUIRED_CODE
        )


class AlphaInviteRequiredError(BaseAppException):
    """Raised when a new account is attempted without an invite link."""

    def __init__(self, message: str = "This alpha is invite-only"):
        super().__init__(
            message=message, status_code=403, error_code=ALPHA_INVITE_REQUIRED_CODE
        )


class AlphaInviteInvalidError(BaseAppException):
    """Raised for any unusable invite; the reason is never disclosed."""

    def __init__(self, message: str = "This invite link is not valid"):
        super().__init__(
            message=message, status_code=403, error_code=ALPHA_INVITE_INVALID_CODE
        )


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


class AccountSuspendedError(BaseAppException):
    """Raised when a suspended alpha tester tries to sign in or refresh."""

    def __init__(self, message: str = "This account is suspended"):
        super().__init__(
            message=message, status_code=403, error_code=ACCOUNT_SUSPENDED_CODE
        )


class AlphaInviteTargetRequiredError(BaseAppException):
    """Raised when an invite is revoked without naming which one."""

    def __init__(self, message: str = "An invite label or id is required"):
        super().__init__(message=message, status_code=400)


class AlphaSurveyAlreadySubmittedError(BaseAppException):
    """Raised when a survey that is answered once is submitted again."""

    def __init__(self, message: str = "This survey was already answered"):
        super().__init__(
            message=message,
            status_code=409,
            error_code=ALPHA_SURVEY_ALREADY_SUBMITTED_CODE,
        )


class AlphaTurnNotFoundError(BaseAppException):
    """Raised when a flagged turn does not exist or is not the user's."""

    def __init__(self, message: str = "Turn not found"):
        super().__init__(message=message, status_code=404)


class AlphaRetentionNotReachedError(BaseAppException):
    """Raised when alpha data is purged before its retention period ended."""

    def __init__(self, retention_date: str):
        super().__init__(
            message=f"Alpha data is kept until {retention_date}", status_code=409
        )
        self.retention_date = retention_date
