from enum import Enum
from typing import Annotated

from pydantic import Field, model_validator

from strategy_contracts.base import StrictModel
from strategy_contracts.enums import Terrain, TroopType
from strategy_contracts.ids import FactionId, Percent, WholeNumber

MAX_FACTOR_PERCENT = 1000
Factor = Annotated[int, Field(ge=0, le=MAX_FACTOR_PERCENT)]
PositiveFactor = Annotated[int, Field(ge=1, le=MAX_FACTOR_PERCENT)]
DEFAULT_ESCAPE_BONUS = {Terrain.FOREST: 10, Terrain.MOUNTAIN: 10, Terrain.MARSH: -10}


class Formation(str, Enum):
    BALANCED = "balanced"
    DEFENSIVE = "defensive"
    CONCENTRATED = "concentrated"


class Tactic(str, Enum):
    HOLD = "hold"
    PRESS = "press"
    FLANK = "flank"
    HOLD_HIGH_GROUND = "hold_high_ground"
    FEIGNED_RETREAT = "feigned_retreat"
    FOREST_FLANK = "forest_flank"
    NIGHT_ATTACK = "night_attack"


class WithdrawalPolicy(str, Enum):
    PRESERVE = "preserve"
    BALANCED = "balanced"
    HOLD_AT_COST = "hold_at_cost"


class ReservePolicy(str, Enum):
    CONSERVE = "conserve"
    REINFORCE_ON_PRESSURE = "reinforce_on_pressure"


class Weather(str, Enum):
    CLEAR = "clear"
    RAIN = "rain"
    SEVERE = "severe"


class SupplyState(str, Enum):
    SUPPLIED = "supplied"
    STRAINED = "strained"
    ISOLATED = "isolated"


class WeatherSeason(str, Enum):
    WINTER = "winter"
    SPRING = "spring"
    OTHER = "other"


class WeatherWeights(StrictModel):
    clear: Percent
    rain: Percent
    severe: Percent

    @model_validator(mode="after")
    def validate_probability_total(self) -> "WeatherWeights":
        if self.clear + self.rain + self.severe != 100:
            raise ValueError("weather probabilities must total 100")
        return self


class BattleTuning(StrictModel):
    rule_version: str = "battle-v1"
    max_exchanges_per_turn: int = Field(default=4, ge=1, le=4)
    command_cost: WholeNumber = 1
    frontage: dict[Terrain, WholeNumber] = Field(
        default_factory=lambda: dict(
            zip(Terrain, (1000, 600, 300, 600, 400, 1000, 1000), strict=True)
        )
    )
    formation_reserve_percent: dict[Formation, Percent] = Field(
        default_factory=lambda: dict(zip(Formation, (25, 40, 10), strict=True))
    )
    formation_attack_percent: dict[Formation, Factor] = Field(
        default_factory=lambda: dict(zip(Formation, (100, 90, 115), strict=True))
    )
    formation_protection_percent: dict[Formation, PositiveFactor] = Field(
        default_factory=lambda: dict(zip(Formation, (100, 115, 90), strict=True))
    )
    tactic_attack_percent: dict[Tactic, Factor] = Field(
        default_factory=lambda: dict(
            zip(Tactic, (95, 110, 110, 100, 105, 108, 112), strict=True)
        )
    )
    tactic_protection_percent: dict[Tactic, PositiveFactor] = Field(
        default_factory=lambda: dict(
            zip(Tactic, (110, 95, 100, 120, 90, 95, 85), strict=True)
        )
    )
    troop_attack: dict[TroopType, WholeNumber] = Field(
        default_factory=lambda: dict(zip(TroopType, (10, 14, 12), strict=True))
    )
    troop_protection: dict[TroopType, PositiveFactor] = Field(
        default_factory=lambda: dict(zip(TroopType, (10, 8, 8), strict=True))
    )
    terrain_flank_allowed: dict[Terrain, bool] = Field(
        default_factory=lambda: {
            terrain: terrain not in (Terrain.MOUNTAIN, Terrain.MARSH, Terrain.FOREST)
            for terrain in Terrain
        }
    )
    cavalry_terrain_attack_percent: dict[Terrain, Factor] = Field(
        default_factory=lambda: {
            terrain: 75
            if terrain in (Terrain.FOREST, Terrain.MARSH, Terrain.MOUNTAIN)
            else 100
            for terrain in Terrain
        }
    )
    defending_archer_attack_percent: dict[Terrain, Factor] = Field(
        default_factory=lambda: {
            terrain: 110 if terrain in (Terrain.HILLS, Terrain.MOUNTAIN) else 100
            for terrain in Terrain
        }
    )
    flank_min_cavalry_percent: Percent = 20
    casualty_rate_percent: Percent = 10
    fatigue_per_exchange: Percent = 8
    unengaged_fatigue_recovery: Percent = 20
    random_damage_min_percent: Factor = 90
    random_damage_max_percent: Factor = 110
    morale_base_loss: Percent = 1
    morale_factor_floor_percent: Percent = 25
    morale_factor_base_percent: Percent = 50
    fatigue_morale_divisor: int = Field(default=2, ge=1)
    forced_rout_morale: Percent = 10
    withdrawal_morale: dict[WithdrawalPolicy, Percent] = Field(
        default_factory=lambda: dict(zip(WithdrawalPolicy, (45, 30, 15), strict=True))
    )
    withdrawal_loss_percent: dict[WithdrawalPolicy, Percent] = Field(
        default_factory=lambda: dict(zip(WithdrawalPolicy, (20, 35, 55), strict=True))
    )
    reserve_pressure_percent: Percent = 20
    escape_base_percent: Percent = 50
    escape_min_percent: Percent = 10
    escape_max_percent: Percent = 90
    escape_morale_divisor: int = Field(default=2, ge=1)
    escape_cavalry_factor: Percent = 20
    terrain_escape_bonus: dict[Terrain, Annotated[int, Field(ge=-100, le=100)]] = Field(
        default_factory=lambda: {
            terrain: DEFAULT_ESCAPE_BONUS.get(terrain, 0) for terrain in Terrain
        }
    )
    rout_escape_penalty: Percent = 20
    pursuit_loss_percent: Percent = 5
    rout_pursuit_loss_percent: Percent = 10
    no_cavalry_pursuit_divisor: int = Field(default=2, ge=1)
    supply_wealth_capacity: WholeNumber = 10
    supply_road_bonus: WholeNumber = 100
    supply_attack_percent: dict[SupplyState, Factor] = Field(
        default_factory=lambda: dict(zip(SupplyState, (100, 90, 75), strict=True))
    )
    supply_extra_fatigue: dict[SupplyState, Percent] = Field(
        default_factory=lambda: dict(zip(SupplyState, (0, 2, 4), strict=True))
    )
    weather_weights: dict[WeatherSeason, WeatherWeights] = Field(
        default_factory=lambda: {
            WeatherSeason.WINTER: WeatherWeights(clear=40, rain=30, severe=30),
            WeatherSeason.SPRING: WeatherWeights(clear=50, rain=40, severe=10),
            WeatherSeason.OTHER: WeatherWeights(clear=75, rain=20, severe=5),
        }
    )
    weather_attack_percent: dict[Weather, Factor] = Field(
        default_factory=lambda: dict(zip(Weather, (100, 95, 85), strict=True))
    )
    weather_protection_percent: dict[Weather, PositiveFactor] = Field(
        default_factory=lambda: {weather: 100 for weather in Weather}
    )
    professional_recon_rating: Percent = 50
    faction_recon_ratings: dict[FactionId, Percent] = Field(default_factory=dict)
    recon_base_percent: Percent = 50
    recon_rating_divisor: int = Field(default=2, ge=1)
    recon_min_percent: Percent = 10
    recon_max_percent: Percent = 90
    terrain_concealment: dict[Terrain, Percent] = Field(
        default_factory=lambda: {
            terrain: 10 if terrain in (Terrain.FOREST, Terrain.MARSH) else 0
            for terrain in Terrain
        }
    )
    deception_penalty: Percent = 20
    capture_base_percent: Percent = 10
    capture_rating_divisor: int = Field(default=5, ge=1)
    capture_min_percent: Percent = 5
    capture_max_percent: Percent = 25
    useful_estimate_width_percent: Percent = 10
    uncertain_estimate_width_percent: Percent = 30
    uncertain_center_error_percent: Percent = 20
    deception_center_shift_percent: Percent = 20
    capture_recon_penalty: Percent = 10
    capture_recon_penalty_cap: Percent = 30
    scout_detention_turns: int = Field(default=1, ge=1)
    scout_extension_turns: int = Field(default=2, ge=1)
    interrogation_useful_percent: Percent = 60
    intent_low_morale: Percent = 30
    intent_advantage_ratio: int = Field(default=2, ge=1)
    intent_morale_bands: tuple[Percent, ...] = (45, 30, 15)

    @model_validator(mode="after")
    def validate_complete_tables(self) -> "BattleTuning":
        for name, field in type(self).model_fields.items():
            annotation = field.annotation
            if getattr(annotation, "__origin__", None) is not dict:
                continue
            key_type = annotation.__args__[0]
            if (
                isinstance(key_type, type)
                and issubclass(key_type, Enum)
                and set(getattr(self, name)) != set(key_type)
            ):
                raise ValueError(f"{name} must define every {key_type.__name__}")
        return self

    @model_validator(mode="after")
    def validate_bounds(self) -> "BattleTuning":
        for prefix in ("random_damage", "escape", "recon", "capture"):
            if getattr(self, f"{prefix}_min_percent") > getattr(
                self, f"{prefix}_max_percent"
            ):
                raise ValueError(f"{prefix} minimum cannot exceed maximum")
        if any(width == 0 for width in self.frontage.values()):
            raise ValueError("frontage must be positive")
        if self.scout_extension_turns <= self.scout_detention_turns:
            raise ValueError("scout extension must exceed default detention")
        return self
