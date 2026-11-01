"""Structured player requests for the authored fantasy profile."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class FantasyActionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_id: Literal["rest", "claim_retrieval_reward"]
