"""Pydantic schemas for scenario invites and the private-scenario allowlist."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class ScenarioInviteResponse(BaseModel):
    """A freshly minted invite link. The token appears only here."""

    url: str
    expires_at: datetime


class ScenarioInviteAcceptResponse(BaseModel):
    scenario_id: uuid.UUID


class ScenarioAccessMember(BaseModel):
    user_id: uuid.UUID
    display_name: str
