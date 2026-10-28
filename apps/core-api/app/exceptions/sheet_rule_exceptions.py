"""Sheet rule (tool `rule_sheet`) exception classes."""

from app.exceptions.base import BaseAppException


class SheetRuleModeError(BaseAppException):
    """Raised when a sheet rule operation targets a non-master-mode scenario."""

    def __init__(
        self, message: str = "Sheet rules are only available for master-mode scenarios"
    ):
        super().__init__(message=message, status_code=422)


class SheetRuleNotFoundError(BaseAppException):
    """Raised when a sheet rule is missing or belongs to another scenario."""

    def __init__(self, message: str = "Sheet rule not found"):
        super().__init__(message=message, status_code=404)


class SheetRuleConflictError(BaseAppException):
    """Raised when a sheet rule's key or number is already used in the scenario."""

    def __init__(self, message: str = "Sheet rule key or number already in use"):
        super().__init__(message=message, status_code=409)


class ReservedStateKeyError(BaseAppException):
    """Raised when the creator's state_schema declares a root the `rule_sheet`
    tool owns (`rule_status`, `rule_flags`) while the tool is on."""

    def __init__(self, message: str = "State key is reserved by the rule sheet tool"):
        super().__init__(message=message, status_code=422)
