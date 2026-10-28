from app.models.base import WorldModel
from pydantic import Field, model_validator
from strategy_contracts.enums import OrderKind, PayLevel, TroopType
from strategy_contracts.ids import (
    ArmyId,
    CommanderId,
    EntityId,
    FactionId,
    Percent,
    RegionId,
    WholeNumber,
)


class ArmyOrderState(WorldModel):
    kind: OrderKind
    target_id: EntityId | None = None


class MarchState(WorldModel):
    from_id: RegionId
    to_id: RegionId
    route: list[RegionId] = Field(default_factory=list)
    leg_progress: WholeNumber = 0
    is_halted: bool = False
    is_returning: bool = False

    @model_validator(mode="after")
    def validate_route_is_a_simple_path(self) -> "MarchState":
        # NOTE: a returning army walks back toward from_id, so to_id is only the
        # far end of the road it is on and a later route may legitimately reach it.
        stops = [self.from_id, *self.route]
        if not self.is_returning:
            stops.append(self.to_id)
        if len(set(stops)) != len(stops) or self.from_id == self.to_id:
            raise ValueError("a march may not revisit a region")
        return self

    @model_validator(mode="after")
    def validate_flags(self) -> "MarchState":
        if self.is_halted and self.route:
            raise ValueError("a halted march carries no route")
        if self.is_returning and (self.is_halted or self.leg_progress == 0):
            raise ValueError("a returning march is moving and has ground to cover")
        return self


class ArmyState(WorldModel):
    id: ArmyId
    owner_id: FactionId
    troops: dict[TroopType, WholeNumber] = Field(default_factory=dict)
    commander_id: CommanderId | None = None
    morale: Percent
    fatigue: Percent = 0
    location_id: RegionId
    order: ArmyOrderState | None = None
    pay_level: PayLevel = PayLevel.FULL
    march: MarchState | None = None
    unpaid_turns: WholeNumber = 0

    @model_validator(mode="after")
    def validate_march_starts_at_location(self) -> "ArmyState":
        if self.march is not None and self.march.from_id != self.location_id:
            raise ValueError("a march must start at the army's location")
        return self
