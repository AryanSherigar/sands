"""Response model for GET /health."""

from typing import Literal

from app.models.base import WorldModel

HEALTH_STATUS_OK: Literal["ok"] = "ok"
HEALTH_STATUS_ERROR: Literal["error"] = "error"


class HealthResponse(WorldModel):
    status: Literal["ok", "error"]
    database: bool
