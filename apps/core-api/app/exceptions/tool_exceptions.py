"""Optional scenario tool exception classes."""

from collections.abc import Sequence

from app.exceptions.base import BaseAppException

TOOL_NOT_ENABLED_CODE = "tool_not_enabled"


class ToolNotEnabledError(BaseAppException):
    """Raised when tool-owned data is written while the tool is off."""

    def __init__(self, tool_key: str):
        super().__init__(
            message=f"Enable the '{tool_key}' tool for this scenario first",
            status_code=409,
            error_code=TOOL_NOT_ENABLED_CODE,
        )
        self.tool_key = tool_key


class UnknownToolError(BaseAppException):
    """Raised when an enabled_tools list names a key outside the registry."""

    def __init__(self, unknown_keys: Sequence[str]):
        super().__init__(
            message=f"Unknown tool keys: {', '.join(unknown_keys)}", status_code=422
        )


class ToolRequiredByError(BaseAppException):
    """Raised when disabling a tool that another enabled tool requires."""

    def __init__(self, tool_key: str, dependents: Sequence[str]):
        super().__init__(
            message=(
                f"Tool '{tool_key}' is required by: {', '.join(dependents)}. "
                "Disable those first"
            ),
            status_code=409,
        )
        self.tool_key = tool_key
        self.dependents = list(dependents)


class ToolsRequireMasterModeError(BaseAppException):
    """Raised when tools are enabled on a non-master-mode scenario."""

    def __init__(self, message: str = "Tools are only available in master mode"):
        super().__init__(message=message, status_code=422)
