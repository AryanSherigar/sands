"""Response model for GET /health."""

from typing import Literal

from pydantic import BaseModel

HEALTH_STATUS_OK: Literal["ok"] = "ok"
HEALTH_STATUS_ERROR: Literal["error"] = "error"


class HealthExtensions(BaseModel):
    vector: bool
    pg_textsearch: bool


class HealthResponse(BaseModel):
    status: Literal["ok", "error"]
    database: bool
    extensions: HealthExtensions
