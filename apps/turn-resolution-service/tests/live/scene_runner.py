import time
import uuid
from dataclasses import dataclass, field

import pytest
import structlog.testing
from app.config import settings
from app.integrations import simulation_client
from app.models.scene import SceneMessageKind, SceneMessageRequest
from app.services import scene_prompt, scene_service, scene_stream_service
from app.services.scene_service import PreparedExchange, SceneUsage
from strategy_contracts.scene import SceneStatus, SceneType, SubmissionStatus
from strategy_contracts.scene_exchange import (
    InternalScenePackage,
    SceneAction,
    SceneDecision,
    SceneExchangeResult,
    SceneExchangeSubmission,
    SceneExchangeView,
    SceneFailureResult,
)

from .budget_loader import live_budget
from .scene_scenarios import SceneScenario, ScriptedTurn

USER_ID = uuid.UUID(int=7)
CHARS_PER_TOKEN = 3
MAX_SCENE_FAILURES = 3
EVENT_DEGRADED = "degraded"
EVENT_NARRATION = "narration"
EVENT_UNPARSEABLE = "scene_decision_unparseable"


@dataclass
class ExchangeRecord:
    kind: SceneMessageKind
    player_text: str
    leader_text: str
    decision: SceneDecision | None
    events: list[tuple[str, str]]
    usage: SceneUsage
    latency_seconds: float
    was_unparseable: bool
    was_degraded: bool
    is_budget_cap_reached: bool = False


@dataclass
class ScenarioResult:
    scenario: SceneScenario
    exchanges: list[ExchangeRecord] = field(default_factory=list)
    was_stopped_by_budget: bool = False
    simulation: "FakeSimulation | None" = None


class FakeSimulation:
    """In-memory stand-in for the simulation service's scene routes."""

    def __init__(self, scenario: SceneScenario) -> None:
        self.package = scenario.package
        self.transcript: list[SceneExchangeView] = []
        self.submissions: list[SceneExchangeSubmission] = []
        self.failure_count = 0

    def _remaining(self) -> int:
        return self.package.exchange_cap - len(self.transcript)

    async def fetch(self, scene_id: uuid.UUID, user_id: uuid.UUID):
        return InternalScenePackage(
            package=self.package,
            status=SceneStatus.OPENED,
            transcript=list(self.transcript),
            exchanges_remaining=self._remaining(),
        )

    async def store_letter_body(self, scene_id, user_id, text: str):
        self.transcript.append(
            SceneExchangeView(sequence=1, player_text="", leader_text=text)
        )
        return SceneExchangeResult(
            status=SubmissionStatus.ACCEPTED,
            scene_status=SceneStatus.OPENED,
            exchanges_remaining=self._remaining(),
        )

    def _status_after(self, submission: SceneExchangeSubmission) -> SceneStatus:
        if self.package.scene_type is not SceneType.LETTER:
            return SceneStatus.OPENED
        is_choice = submission.decision.action is SceneAction.CHOOSE_OPTION
        return SceneStatus.RESOLVED if is_choice else SceneStatus.DEFAULTED

    async def submit(self, scene_id, user_id, submission: SceneExchangeSubmission):
        self.submissions.append(submission)
        self.transcript.append(
            SceneExchangeView(
                sequence=submission.sequence,
                player_text=submission.player_text,
                leader_text=submission.leader_text,
            )
        )
        return SceneExchangeResult(
            status=SubmissionStatus.ACCEPTED,
            scene_status=self._status_after(submission),
            exchanges_remaining=self._remaining(),
        )

    async def report_failure(self, scene_id, user_id):
        self.failure_count += 1
        return SceneFailureResult(
            scene_status=SceneStatus.OPENED,
            failed_attempts=self.failure_count,
            attempts_remaining=max(0, MAX_SCENE_FAILURES - self.failure_count),
        )

    def install(self, patcher: pytest.MonkeyPatch) -> None:
        patcher.setattr(simulation_client, "fetch_scene_package", self.fetch)
        patcher.setattr(simulation_client, "submit_exchange", self.submit)
        patcher.setattr(simulation_client, "store_letter_body", self.store_letter_body)
        patcher.setattr(simulation_client, "report_scene_failure", self.report_failure)


def _input_bound(prepared: PreparedExchange) -> int:
    system = scene_prompt.build_system_instruction(prepared.package)
    history = sum(
        len(item.player_text) + len(item.leader_text) for item in prepared.transcript
    )
    characters = (
        len(system) + history + len(prepared.player_text) + len(prepared.current_draft)
    )
    return (
        2 * (characters // CHARS_PER_TOKEN + 1) + settings.scene_reply_max_output_tokens
    )


def _output_bound() -> int:
    limits = (
        settings.scene_reply_max_output_tokens
        + settings.scene_decision_max_output_tokens
    )
    return limits + 2 * settings.scene_reasoning_headroom_tokens


def _charge(budget, usage: SceneUsage) -> bool:
    try:
        budget.charge(usage.prompt_tokens, usage.completion_tokens, usage.cached_tokens)
    except live_budget.LiveBudgetExhausted:
        return True
    return False


async def _stream(prepared: PreparedExchange, usage: SceneUsage):
    with structlog.testing.capture_logs() as logs:
        events = [
            (event.event, event.data)
            async for event in scene_stream_service.stream_prepared_message(
                prepared, usage
            )
        ]
    return events, logs


def _request_for(turn: str | ScriptedTurn) -> SceneMessageRequest:
    if isinstance(turn, str):
        return SceneMessageRequest(text=turn)
    return SceneMessageRequest(
        kind=turn.kind, text=turn.text, current_draft=turn.current_draft
    )


async def run_exchange(
    simulation: FakeSimulation, turn: str | ScriptedTurn, budget
) -> ExchangeRecord | None:
    request = _request_for(turn)
    prepared = await scene_service.prepare_exchange(
        simulation.package.scene_id, USER_ID, request
    )
    if budget.would_exceed(_input_bound(prepared), _output_bound()):
        return None
    usage, submitted = SceneUsage(), len(simulation.submissions)
    started = time.perf_counter()
    events, logs = await _stream(prepared, usage)
    latency = time.perf_counter() - started
    has_new_submission = len(simulation.submissions) > submitted
    return ExchangeRecord(
        kind=request.kind,
        player_text=request.text,
        leader_text="".join(data for name, data in events if name == EVENT_NARRATION),
        decision=simulation.submissions[-1].decision if has_new_submission else None,
        events=events,
        usage=usage,
        latency_seconds=latency,
        was_unparseable=any(entry["event"] == EVENT_UNPARSEABLE for entry in logs),
        was_degraded=any(name == EVENT_DEGRADED for name, _ in events),
        is_budget_cap_reached=_charge(budget, usage),
    )


async def run_scenario(
    scenario: SceneScenario, budget, patcher: pytest.MonkeyPatch
) -> ScenarioResult:
    simulation = FakeSimulation(scenario)
    simulation.install(patcher)
    result = ScenarioResult(scenario=scenario, simulation=simulation)
    for turn in scenario.player_turns:
        record = await run_exchange(simulation, turn, budget)
        if record is None:
            result.was_stopped_by_budget = True
            break
        result.exchanges.append(record)
        if record.is_budget_cap_reached or record.was_degraded:
            result.was_stopped_by_budget = record.is_budget_cap_reached
            break
    return result
