from enum import Enum

from app.models.base import WorldModel
from app.models.battle_intelligence import ReconReport, StrengthInterval
from pydantic import Field, field_validator, model_validator
from strategy_contracts.battle import (
    Formation,
    ReservePolicy,
    SupplyState,
    Tactic,
    Weather,
    WithdrawalPolicy,
)
from strategy_contracts.enums import Terrain, TroopType
from strategy_contracts.ids import ArmyId, FactionId, Percent, RegionId, WholeNumber


class BattleAction(str, Enum):
    TAKE_COMMAND = "take_command"
    DELEGATE_BATTLE = "delegate_battle"
    SET_PLAN = "set_plan"
    COMMIT_RESERVES = "commit_reserves"
    RECONNOITRE = "reconnoitre"
    DECEIVE = "deceive"
    WITHDRAW = "withdraw"
    SURRENDER = "surrender"
    CAPTURE_DECISION = "capture_decision"


class BattleStatus(str, Enum):
    AWAITING_COMMANDS = "awaiting_commands"
    AWAITING_NEXT_TURN = "awaiting_next_turn"
    RESOLVED = "resolved"


class BattleSignificance(str, Enum):
    COMMITTED_STRENGTH = "committed_strength"
    CAPITAL_REGION = "capital_region"
    CLAIMED_REGION = "claimed_region"
    IMPORTANT_COMMANDER = "important_commander"


class BattleControlMode(str, Enum):
    UNDECIDED = "undecided"
    PLAYER = "player"
    DELEGATED = "delegated"


class BattleOutcome(str, Enum):
    ATTACKER_VICTORY = "attacker_victory"
    DEFENDER_VICTORY = "defender_victory"
    MUTUAL_DISENGAGEMENT = "mutual_disengagement"
    ATTACKER_SURRENDER = "attacker_surrender"
    DEFENDER_SURRENDER = "defender_surrender"
    MUTUAL_SURRENDER = "mutual_surrender"


class ContingentStatus(str, Enum):
    FIGHTING = "fighting"
    WITHDRAWING = "withdrawing"
    WITHDRAWN = "withdrawn"
    ROUTED = "routed"
    SURRENDERED = "surrendered"
    DESTROYED = "destroyed"


class BattleSide(str, Enum):
    ATTACKER = "attacker"
    DEFENDER = "defender"


class StandingPlan(WorldModel):
    formation: Formation = Formation.BALANCED
    tactic: Tactic = Tactic.HOLD
    withdrawal_policy: WithdrawalPolicy = WithdrawalPolicy.BALANCED
    reserve_policy: ReservePolicy = ReservePolicy.CONSERVE


class ArmyDeployment(WorldModel):
    """An allocation snapshot, reconciled from authoritative ArmyState on each boundary."""

    army_id: ArmyId
    available: dict[TroopType, WholeNumber]
    active: dict[TroopType, WholeNumber] = Field(default_factory=dict)
    reserve: dict[TroopType, WholeNumber] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_troop_partition(self) -> "ArmyDeployment":
        for troop_type in TroopType:
            deployed = self.active.get(troop_type, 0) + self.reserve.get(troop_type, 0)
            if deployed != self.available.get(troop_type, 0):
                raise ValueError("deployment must partition available troops")
        return self


class BattleContingent(WorldModel):
    faction_id: FactionId
    side: BattleSide
    army_ids: list[ArmyId]
    entry_troops: WholeNumber
    plan: StandingPlan = Field(default_factory=StandingPlan)
    status: ContingentStatus = ContingentStatus.FIGHTING
    desired_active: WholeNumber = 0
    has_committed_reserves: bool = False
    deployments: dict[ArmyId, ArmyDeployment] = Field(default_factory=dict)
    supply: SupplyState | None = None
    intent_id: str | None = None
    deception_expires_exchange: WholeNumber | None = None
    recon_penalty: Percent = 0
    retreat_destination_id: RegionId | None = None
    has_pursuit_resolved: bool = False

    @model_validator(mode="after")
    def validate_deployment_membership(self) -> "BattleContingent":
        if len(self.army_ids) != len(set(self.army_ids)):
            raise ValueError("contingent army ids must be distinct")
        for army_id, deployment in self.deployments.items():
            if army_id != deployment.army_id or army_id not in self.army_ids:
                raise ValueError("deployment must belong to a contingent army")
        self.army_ids.sort()
        return self


class BattleState(WorldModel):
    id: str
    region_id: RegionId
    attacker_army_ids: list[ArmyId]
    defender_army_ids: list[ArmyId]
    attacker_lead_faction_id: FactionId | None = None
    defender_lead_faction_id: FactionId | None = None
    region_controller_id: FactionId | None = None
    created_turn: WholeNumber = 0
    current_turn: WholeNumber = 0
    exchanges_used: int = Field(default=0, ge=0, le=4)
    total_exchanges: WholeNumber = 0
    status: BattleStatus = BattleStatus.AWAITING_COMMANDS
    outcome: BattleOutcome | None = None
    is_big: bool = False
    significance_reasons: list[BattleSignificance] = Field(default_factory=list)
    control_mode: BattleControlMode = BattleControlMode.UNDECIDED
    terrain: Terrain | None = None
    weather: Weather | None = None
    weather_turn: WholeNumber | None = None
    contingents: dict[FactionId, BattleContingent] = Field(default_factory=dict)
    report_ids: list[str] = Field(default_factory=list)
    mission_ids: list[str] = Field(default_factory=list)
    capture_ids: list[str] = Field(default_factory=list)
    deferred_command_ids: list[str] = Field(default_factory=list)

    @field_validator("attacker_army_ids", "defender_army_ids")
    @classmethod
    def validate_distinct_membership(cls, army_ids: list[ArmyId]) -> list[ArmyId]:
        if len(army_ids) != len(set(army_ids)):
            raise ValueError("battle membership must be distinct")
        return sorted(army_ids)

    @model_validator(mode="after")
    def validate_membership(self) -> "BattleState":
        if set(self.attacker_army_ids) & set(self.defender_army_ids):
            raise ValueError("army cannot belong to both battle sides")
        if self.total_exchanges < self.exchanges_used:
            raise ValueError("total exchanges cannot be below current turn usage")
        if self.outcome is not None and self.status != BattleStatus.RESOLVED:
            raise ValueError("only resolved battles have an outcome")
        for faction_id, contingent in self.contingents.items():
            if faction_id != contingent.faction_id:
                raise ValueError("contingent key must match faction")
            members = (
                self.attacker_army_ids
                if contingent.side == BattleSide.ATTACKER
                else self.defender_army_ids
            )
            if not set(contingent.army_ids) <= set(members):
                raise ValueError("contingent armies must belong to their battle side")
        return self

    @model_validator(mode="after")
    def validate_unique_contingent_membership(self) -> "BattleState":
        assigned_armies: set[ArmyId] = set()
        for contingent in self.contingents.values():
            if assigned_armies.intersection(contingent.army_ids):
                raise ValueError("army cannot belong to more than one contingent")
            assigned_armies.update(contingent.army_ids)
        return self


class LossAccounting(WorldModel):
    army_id: ArmyId
    before: dict[TroopType, WholeNumber]
    survivors: dict[TroopType, WholeNumber]
    combat_losses: dict[TroopType, WholeNumber] = Field(default_factory=dict)
    pursuit_losses: dict[TroopType, WholeNumber] = Field(default_factory=dict)
    captives: dict[TroopType, WholeNumber] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_conservation(self) -> "LossAccounting":
        for troop_type in TroopType:
            accounted = sum(
                counts.get(troop_type, 0)
                for counts in (
                    self.survivors,
                    self.combat_losses,
                    self.pursuit_losses,
                    self.captives,
                )
            )
            if accounted != self.before.get(troop_type, 0):
                raise ValueError("exchange losses must conserve soldiers")
        return self


class RetreatResolution(WorldModel):
    faction_id: FactionId
    destination_id: RegionId | None
    has_succeeded: bool


class ExchangeReceipt(WorldModel):
    battle_id: str
    campaign_turn: WholeNumber
    exchange_index: int = Field(ge=1, le=4)
    total_exchange: int = Field(ge=1)
    input_hash: str
    output_hash: str
    rule_version: str
    command_ids: list[str] = Field(default_factory=list)
    intent_ids: list[str] = Field(default_factory=list)
    accounting: list[LossAccounting] = Field(default_factory=list)
    retreats: list[RetreatResolution] = Field(default_factory=list)
    outcome: BattleOutcome | None = None


class ContingentView(WorldModel):
    faction_id: FactionId
    army_ids: list[ArmyId]
    troops: dict[TroopType, WholeNumber]
    morale: Percent
    fatigue: Percent
    plan: StandingPlan
    supply: SupplyState
    status: ContingentStatus


class OpponentView(WorldModel):
    faction_id: FactionId
    strength: StrengthInterval
    reports: list[ReconReport] = Field(default_factory=list)


class BattleView(WorldModel):
    id: str
    region_id: RegionId
    status: BattleStatus
    outcome: BattleOutcome | None
    current_turn: WholeNumber
    exchanges_used: int = Field(ge=0, le=4)
    total_exchanges: WholeNumber
    is_big: bool = False
    control_mode: BattleControlMode = BattleControlMode.UNDECIDED
    terrain: Terrain
    weather: Weather
    own_contingent: ContingentView | None = None
    opponents: list[OpponentView] = Field(default_factory=list)
    legal_commands: list[BattleAction] = Field(default_factory=list)
    command_cost: WholeNumber = 1


class ExchangeReport(WorldModel):
    battle_id: str
    campaign_turn: WholeNumber
    exchange_index: int = Field(ge=1, le=4)
    total_exchange: int = Field(ge=1)
    own_losses: dict[TroopType, WholeNumber] = Field(default_factory=dict)
    opponent_strength: StrengthInterval
    outcome: BattleOutcome | None = None
    observations: list[ReconReport] = Field(default_factory=list)
