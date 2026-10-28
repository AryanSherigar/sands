import uuid

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    user_id: uuid.UUID
    display_name: str
    onboarding_completed: bool = False
    show_mature: bool = False

    model_config = ConfigDict(from_attributes=True)


class TokenExchangeRequest(BaseModel):
    firebase_id_token: str
    invite_code: str | None = None
    alpha_consent_version: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    is_account_restored: bool = False
