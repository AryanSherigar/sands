"""Pydantic v2 domain schemas for User Profile and stats."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

MAX_PREFERRED_GENRES = 3


class UserStatsResponse(BaseModel):
    """Aggregate adventure and creator statistics."""

    campaigns_played_count: int
    victories_count: int
    total_turns_taken: int
    scenarios_authored_count: int
    total_plays_received: int


class UserPublicProfileResponse(BaseModel):
    """Publicly visible user profile details."""

    user_id: uuid.UUID
    display_name: str
    bio: str | None = None
    avatar_url: str | None = None
    banner_url: str | None = None
    created_at: datetime
    stats: UserStatsResponse

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(UserPublicProfileResponse):
    """Full user profile for authenticated owner."""

    auth_provider_id: str
    voice_output_enabled: bool = False
    show_mature: bool = False
    preferred_genres: list[str] = Field(default_factory=list)
    onboarding_completed_at: datetime | None = None
    alpha_consent_is_current: bool = True


class UserProfileUpdate(BaseModel):
    """Request payload for updating user profile."""

    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    bio: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = Field(default=None, max_length=1024)
    banner_url: str | None = Field(default=None, max_length=1024)
    voice_output_enabled: bool | None = Field(default=None)
    show_mature: bool | None = Field(default=None)
    preferred_genres: (
        list[Annotated[str, Field(min_length=1, max_length=100)]] | None
    ) = Field(default=None, max_length=MAX_PREFERRED_GENRES)


class OnboardingCompleteRequest(BaseModel):
    """Request payload for finishing or deferring the first-run setup wizard."""

    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    bio: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = Field(default=None, max_length=1024)
    banner_url: str | None = Field(default=None, max_length=1024)
    preferred_genres: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list, max_length=MAX_PREFERRED_GENRES
    )


class UserPlaythroughSummary(BaseModel):
    """Playthrough session card summary for user campaigns tab."""

    playthrough_id: uuid.UUID
    scenario_id: uuid.UUID
    scenario_title: str
    scenario_mode: str
    cover_image_url: str | None = None
    turn_count: int
    status: str
    ended_outcome_tag: str | None = None
    ended_outcome_title: str | None = None
    ended_outcome_text: str | None = None
    character_name: str | None = None
    character_archetype: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserReviewSummary(BaseModel):
    """Summary of a scenario review written by the user."""

    review_id: uuid.UUID
    scenario_id: uuid.UUID
    scenario_title: str
    rating: int
    review_text: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
