"""Request and response models for optional scenario tools."""

from app.tools.registry import TOOLS
from pydantic import BaseModel, Field


class ToolsUpdate(BaseModel):
    enabled_tools: list[str] = Field(default_factory=list, max_length=len(TOOLS))


class ToolsResponse(BaseModel):
    enabled_tools: list[str]
    auto_enabled: list[str]
    inert_data: dict[str, int]
