from enum import Enum
from typing import Literal

from pydantic import Field, field_validator

from strategy_contracts.base import StrictModel


class ProclamationDomain(str, Enum):
    MARTIAL_LEVIES = "martial_levies"
    EMERGENCY_TAXATION = "emergency_taxation"
    RELIGIOUS_ORTHODOXY = "religious_orthodoxy"
    NOBLE_PRIVILEGES = "noble_privileges"
    POPULAR_RELIEF = "popular_relief"


class ProclamationBurden(str, Enum):
    LIGHT = "light"
    MODERATE = "moderate"
    SEVERE = "severe"
    RADICAL = "radical"


class EstatePillar(str, Enum):
    NOBILITY = "nobility"
    MILITARY = "military"
    BURGHERS = "burghers"
    CLERGY = "clergy"


ProclamationVerdict = Literal["fiat", "compromise"]


class ProclamationDraft(StrictModel):
    is_recognized: bool
    fallback_reason: str | None = None
    domain: ProclamationDomain | None = None
    burden: ProclamationBurden | None = None
    target_estate: EstatePillar | None = None
    concession_estate: EstatePillar | None = None
    legal_summary: str = Field(..., max_length=280)


class ProclamationMinisterView(StrictModel):
    estate: EstatePillar
    title: str
    stance: Literal["support", "cautious", "oppose"]
    primary_grievance: str


class ActiveProclamation(StrictModel):
    id: str
    legal_summary: str
    domain: ProclamationDomain
    burden: ProclamationBurden
    enacted_turn: int
    remaining_turns: int = 4
    immediate_deltas: dict[str, int]
    ongoing_modifiers: dict[str, int]

    @field_validator("ongoing_modifiers", mode="before")
    @classmethod
    def drop_legacy_fractional_modifiers(cls, value: object) -> object:
        if isinstance(value, dict) and any(
            isinstance(item, float) for item in value.values()
        ):
            return {}
        return value


class ProclamationScenePackage(StrictModel):
    scene_id: str
    draft: ProclamationDraft
    ministers: list[ProclamationMinisterView]
    exchange_cap: int = 6
    is_rescinding_previous: bool = False
