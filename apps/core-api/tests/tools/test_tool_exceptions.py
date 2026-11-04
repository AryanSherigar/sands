from app.exceptions.base import BaseAppException
from app.exceptions.tool_exceptions import (
    ToolNotEnabledError,
    ToolRequiredByError,
    ToolsRequireMasterModeError,
    UnknownToolError,
)


def test_tool_not_enabled_is_409_with_code_and_names_the_tool() -> None:
    error = ToolNotEnabledError("atmosphere")

    assert isinstance(error, BaseAppException)
    assert error.status_code == 409
    assert error.error_code == "tool_not_enabled"
    assert "atmosphere" in error.message


def test_tool_required_by_names_dependents() -> None:
    error = ToolRequiredByError("status_hud", ["atmosphere"])

    assert error.status_code == 409
    assert "atmosphere" in error.message


def test_unknown_tool_is_422() -> None:
    assert UnknownToolError(["x"]).status_code == 422


def test_tools_require_master_mode_is_422() -> None:
    assert ToolsRequireMasterModeError().status_code == 422
