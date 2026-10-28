from app.engine.battles.deception import false_hint
from app.engine.battles.reconnaissance import contact_strength, intelligence_id
from app.engine.battles.state import PERCENT
from app.engine.rng import derive_rng
from app.exceptions.base import SimulationServiceError
from app.models.base import WorldModel
from app.models.battle_intelligence import (
    CaptureDecision,
    Confidence,
    ReconReport,
    ScoutCapture,
    ScoutCaptureStatus,
)
from app.models.world_battle import BattleState
from app.models.world_state import WorldState
from pydantic import Field
from strategy_contracts.scenario import StrategyScenario


class CaptureResolution(WorldModel):
    capture: ScoutCapture
    report: ReconReport | None = None


class CaptureExpiry(WorldModel):
    captures: dict[str, ScoutCapture] = Field(default_factory=dict)
    battles: dict[str, BattleState] = Field(default_factory=dict)


def refresh_penalties(
    world: WorldState, battle: BattleState, scenario: StrategyScenario
) -> None:
    for faction_id, contingent in sorted(battle.contingents.items()):
        penalty = sum(
            capture.recon_penalty
            for capture in world.scout_captures.values()
            if capture.battle_id == battle.id
            and capture.origin_faction_id == faction_id
            and capture.status == ScoutCaptureStatus.DETAINED
            and capture.expires_turn > world.clock.turn
        )
        contingent.recon_penalty = min(
            scenario.tuning.battle.capture_recon_penalty_cap, penalty
        )


def expire_captures(world: WorldState, scenario: StrategyScenario) -> CaptureExpiry:
    """Return campaign-owned replacements, including resolved battles; polling is inert."""
    owned = world.model_copy(deep=True)
    result = CaptureExpiry()
    for identity, capture in sorted(owned.scout_captures.items()):
        if (
            capture.status != ScoutCaptureStatus.DETAINED
            or capture.expires_turn > owned.clock.turn
        ):
            continue
        capture.status = ScoutCaptureStatus.RELEASED
        result.captures[identity] = capture
    affected = {capture.battle_id for capture in result.captures.values()}
    for battle in owned.battles:
        if battle.id in affected:
            refresh_penalties(owned, battle, scenario)
            result.battles[battle.id] = battle
    return result


def _interrogation_report(
    world: WorldState, capture: ScoutCapture, scenario: StrategyScenario
) -> ReconReport:
    battle = next(battle for battle in world.battles if battle.id == capture.battle_id)
    rng = derive_rng(
        world.rng.seed, world.clock.turn, "scout_interrogation", capture.id
    )
    is_useful = rng.roll(PERCENT) < scenario.tuning.battle.interrogation_useful_percent
    hint = capture.briefing_hint
    if hint is not None and not is_useful:
        hint = false_hint(hint)
    origin = battle.contingents.get(capture.origin_faction_id)
    total = origin.entry_troops if origin else 0
    return ReconReport(
        id=intelligence_id("interrogation", capture.id),
        battle_id=battle.id,
        observer_faction_id=capture.captor_faction_id,
        subject_faction_id=capture.origin_faction_id,
        mission_id=capture.mission_id,
        target=capture.mission_target,
        observed_turn=world.clock.turn,
        observed_exchange=battle.total_exchanges + 1,
        available_from_wave=battle.exchanges_used + 2,
        strength=contact_strength(total),
        preparation_hint=hint,
        confidence=Confidence.MEDIUM if is_useful else Confidence.LOW,
    )


def resolve_capture_decision(
    world: WorldState,
    capture_id: str,
    captor_faction_id: str,
    decision: CaptureDecision,
    scenario: StrategyScenario,
) -> CaptureResolution:
    """Validate one decision; the owning reducer applies the replacement and report."""
    original = world.scout_captures.get(capture_id)
    _validate_decision(original, captor_faction_id, world.clock.turn)
    capture = original.model_copy(deep=True)
    capture.has_decided = True
    capture.decision = decision
    result = CaptureResolution(capture=capture)
    if decision == CaptureDecision.DETAIN:
        capture.has_extended = True
        capture.expires_turn = (
            capture.captured_turn + scenario.tuning.battle.scout_extension_turns
        )
    elif decision == CaptureDecision.RELEASE:
        capture.status = ScoutCaptureStatus.RELEASED
    elif not capture.has_leaked:
        result.report = _interrogation_report(world, capture, scenario)
        capture.has_leaked = True
    return result


def _validate_decision(
    capture: ScoutCapture | None, captor_faction_id: str, campaign_turn: int
) -> None:
    if (
        capture is None
        or capture.captor_faction_id != captor_faction_id
        or capture.has_decided
        or capture.has_extended
        or capture.status != ScoutCaptureStatus.DETAINED
        or capture.expires_turn <= campaign_turn
    ):
        raise SimulationServiceError("capture decision is unavailable")
