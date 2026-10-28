import uuid

from pydantic import BaseModel


class AlphaConfigResponse(BaseModel):
    is_alpha_mode: bool
    is_signup_enabled: bool
    consent_version: str | None
    scenario_id: uuid.UUID | None
    tension_prompt_every_turns: int | None = None


class AlphaConsentRequest(BaseModel):
    version: str
