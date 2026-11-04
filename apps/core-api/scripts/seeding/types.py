"""What a generator must hand to the shared persistence code."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.models.condition import ConditionCreate
from app.models.end_condition import EndConditionCreate
from app.models.entity import EntityCreate
from app.models.fact import FactCreate
from app.models.invariant import InvariantCreate
from app.models.minigame import MinigameCreate
from app.models.rule_check import RuleCheckCreate
from app.models.sheet_rule import SheetRuleCreate


@dataclass(frozen=True)
class EntitySeed:
    slug: str
    payload: EntityCreate


@dataclass(frozen=True)
class PinSeed:
    slug: str
    x: float
    y: float


@dataclass(frozen=True)
class MapSeed:
    name: str
    image_url: str | None
    pins: Sequence[PinSeed]
    connections: Sequence[tuple[str, str]]
    start_slug: str | None = None
    display_order: int = 0


class SeedableScenario(Protocol):
    @property
    def scenario(self) -> dict[str, object]: ...

    @property
    def entities(self) -> Sequence[EntitySeed]: ...

    @property
    def facts(self) -> Sequence[FactCreate]: ...

    @property
    def conditions(self) -> Sequence[ConditionCreate]: ...

    @property
    def end_conditions(self) -> Sequence[EndConditionCreate]: ...

    @property
    def invariants(self) -> Sequence[InvariantCreate]: ...

    @property
    def minigames(self) -> Sequence[MinigameCreate]: ...

    @property
    def rule_checks(self) -> Sequence[RuleCheckCreate]: ...

    @property
    def sheet_rules(self) -> Sequence[SheetRuleCreate]: ...
