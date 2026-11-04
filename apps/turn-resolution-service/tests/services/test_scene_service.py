import json
import uuid

import pytest
import structlog.testing
from app.config import settings
from app.exceptions.scene_exceptions import (
    SceneNotOpenError,
    SimulationUnavailableError,
)
from app.exceptions.turn_exceptions import LlmUnavailableError
from app.integrations import openai_compatible_client, simulation_client
from app.models.scene import SceneMessageRequest
from app.services import scene_prompt, scene_service
from strategy_contracts.scene import (
    AcceptanceRange,
    HiddenLimits,
    Participant,
    ParticipantKind,
    ScenePackage,
    SceneSituation,
    SceneStatus,
    SceneType,
    SubmissionStatus,
    TermsCardOutcome,
    TermsCardSpec,
    TermsResult,
)
from strategy_contracts.scene_exchange import (
    InternalScenePackage,
    SceneAction,
    SceneExchangeResult,
    SceneFailureResult,
)
from strategy_contracts.terms import NonAggressionTerm, TermKind, TermsCard

SCENE_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
LEADER_REPLY = "Eight turns, and not a day less."
DECISION_MARKER = "Answer with only a JSON"


def _package() -> ScenePackage:
    return ScenePackage(
        scene_id=SCENE_ID,
        playthrough_id=uuid.uuid4(),
        scene_type=SceneType.NEGOTIATION,
        turn=1,
        situation=SceneSituation(summary="A pact is sought."),
        participants=[
            Participant(participant_id="mira", kind=ParticipantKind.LEADER, name="Mira")
        ],
        hidden_limits=HiddenLimits(
            acceptance=AcceptanceRange(accept_at=48, haggle_at=28)
        ),
        allowed_outcomes=[
            TermsCardSpec(
                allowed_term_kinds=[TermKind.NON_AGGRESSION],
                price_by_term_kind={TermKind.NON_AGGRESSION: 6},
            )
        ],
        exchange_cap=6,
        default_outcome=TermsCardOutcome(result=TermsResult.REFUSED),
    )


def _fetched(status: SceneStatus = SceneStatus.OPENED, remaining: int = 6):
    return InternalScenePackage(
        package=_package(), status=status, exchanges_remaining=remaining
    )


def _result(**overrides) -> SceneExchangeResult:
    body = {
        "status": SubmissionStatus.ACCEPTED,
        "scene_status": SceneStatus.OPENED,
        "exchanges_remaining": 5,
    }
    return SceneExchangeResult(**(body | overrides))


class Harness:
    def __init__(self, monkeypatch, decision_text: str = '{"action": "continue_talk"}'):
        self.submissions = []
        self.systems = []
        self.decision_text = decision_text
        self.result = _result()
        self.submit_error = None
        self.reply_error = None
        self.decision_error = None
        self.failure_reports = []
        self.report_status = SceneStatus.OPENED
        self.report_error = None
        monkeypatch.setattr(openai_compatible_client, "stream_chat", self._stream)
        monkeypatch.setattr(simulation_client, "report_scene_failure", self._report)
        monkeypatch.setattr(simulation_client, "submit_exchange", self._submit)

    async def _stream(self, system_instruction, contents, **_):
        self.systems.append(system_instruction)
        is_decision = DECISION_MARKER in contents[-1].parts[0].text
        error = self.decision_error if is_decision else self.reply_error
        if error is not None:
            raise error
        for piece in (
            [self.decision_text]
            if is_decision
            else ["Eight turns, ", "and not a day less."]
        ):
            yield piece

    async def _report(self, scene_id, user_id):
        if self.report_error is not None:
            raise self.report_error
        self.failure_reports.append(scene_id)
        return SceneFailureResult(
            scene_status=self.report_status, failed_attempts=1, attempts_remaining=2
        )

    async def _submit(self, scene_id, user_id, submission):
        if self.submit_error is not None:
            raise self.submit_error
        self.submissions.append((scene_id, user_id, submission))
        return self.result


async def _events(prepared):
    return [
        (event.event, event.data)
        async for event in scene_service.stream_scene_message(prepared)
    ]


def _prepared():
    return scene_service.PreparedExchange(
        scene_id=SCENE_ID,
        user_id=USER_ID,
        package=_package(),
        transcript=[],
        player_text="Will you sign a pact?",
    )


async def test_prepare_rejects_a_finished_or_exhausted_scene(monkeypatch) -> None:
    request = SceneMessageRequest(text="hello")
    for fetched in (_fetched(SceneStatus.RESOLVED), _fetched(remaining=0)):

        async def fake_fetch(scene_id, user_id, fetched=fetched):
            return fetched

        monkeypatch.setattr(simulation_client, "fetch_scene_package", fake_fetch)
        with pytest.raises(SceneNotOpenError):
            await scene_service.prepare_exchange(SCENE_ID, USER_ID, request)


async def test_prepare_returns_the_package_and_transcript(monkeypatch) -> None:
    async def fake_fetch(scene_id, user_id):
        return _fetched()

    monkeypatch.setattr(simulation_client, "fetch_scene_package", fake_fetch)
    prepared = await scene_service.prepare_exchange(
        SCENE_ID, USER_ID, SceneMessageRequest(text="hello")
    )
    assert (prepared.sequence, prepared.player_text) == (1, "hello")


async def test_a_continuing_exchange_streams_then_records_and_finishes(
    monkeypatch,
) -> None:
    harness = Harness(monkeypatch)
    events = await _events(_prepared())
    assert [name for name, _ in events] == ["narration", "narration", "done"]
    assert "".join(data for name, data in events if name == "narration") == LEADER_REPLY
    scene_id, user_id, submission = harness.submissions[0]
    assert (scene_id, user_id) == (SCENE_ID, USER_ID)
    assert submission.sequence == 1
    assert submission.leader_text == LEADER_REPLY
    assert submission.decision.action is SceneAction.CONTINUE_TALK
    assert submission.tone_grade == 2
    assert json.loads(events[-1][1]) == {
        "sequence": 1,
        "exchanges_remaining": 5,
        "scene_status": "opened",
        "tone_grade": 2,
    }


async def test_the_private_brief_reaches_the_model_only_as_system_text(
    monkeypatch,
) -> None:
    harness = Harness(monkeypatch)
    events = await _events(_prepared())
    assert "agree outright" in harness.systems[0]
    assert all("agree outright" not in data for _, data in events)


async def test_a_proposal_and_a_scene_end_are_reported_in_order(monkeypatch) -> None:
    harness = Harness(monkeypatch, '{"action": "propose_terms", "duration_turns": 8}')
    card = TermsCard(
        proposer_id="house_carrow",
        counterpart_id="house_ashford",
        terms=[
            NonAggressionTerm(
                faction_a="house_carrow", faction_b="house_ashford", duration_turns=8
            )
        ],
    )
    harness.result = _result(pending_proposal=card)
    events = await _events(_prepared())
    assert [name for name, _ in events][-2:] == ["proposal", "done"]
    assert harness.submissions[0][2].decision.duration_turns == 8
    harness.result = _result(scene_status=SceneStatus.RESOLVED)
    ended = await _events(_prepared())
    assert [name for name, _ in ended][-2:] == ["scene_ended", "done"]


@pytest.mark.parametrize(
    "failure",
    ["reply_error", "submit_error"],
)
async def test_failures_degrade_without_recording_a_message(
    monkeypatch, failure
) -> None:
    harness = Harness(monkeypatch)
    error = (
        LlmUnavailableError()
        if failure == "reply_error"
        else SimulationUnavailableError()
    )
    setattr(harness, failure, error)
    events = await _events(_prepared())
    assert events[-1][0] == "degraded"
    assert "done" not in [name for name, _ in events]


async def test_a_failed_decision_call_still_records_the_reply(monkeypatch) -> None:
    harness = Harness(monkeypatch)
    harness.decision_error = LlmUnavailableError()
    events = await _events(_prepared())
    assert events[-1][0] == "done"
    assert harness.submissions[0][2].decision.action is SceneAction.CONTINUE_TALK


async def test_a_rejected_submission_degrades(monkeypatch) -> None:
    harness = Harness(monkeypatch)
    harness.result = _result(status=SubmissionStatus.REJECTED, reason="out_of_order")
    events = await _events(_prepared())
    assert events[-1][0] == "degraded"


async def test_prompt_module_directives_are_what_the_harness_keys_on() -> None:
    assert DECISION_MARKER in scene_prompt.DECISION_DIRECTIVE


async def test_a_narration_failure_is_reported_once_and_the_scene_stays_open(
    monkeypatch,
) -> None:
    harness = Harness(monkeypatch)
    harness.reply_error = LlmUnavailableError()
    events = await _events(_prepared())
    assert events[-1] == ("degraded", scene_service.DEGRADED_MESSAGE)
    assert harness.failure_reports == [SCENE_ID]


async def test_the_final_failure_tells_the_player_the_scene_ended(monkeypatch) -> None:
    harness = Harness(monkeypatch)
    harness.reply_error = LlmUnavailableError()
    harness.report_status = SceneStatus.DEFAULTED
    events = await _events(_prepared())
    assert events[-1] == ("degraded", scene_service.DEGRADED_ENDED_MESSAGE)


async def test_a_simulation_outage_is_not_counted_as_a_narration_failure(
    monkeypatch,
) -> None:
    harness = Harness(monkeypatch)
    harness.submit_error = SimulationUnavailableError()
    events = await _events(_prepared())
    assert events[-1][0] == "degraded"
    assert harness.failure_reports == []


async def test_a_failed_failure_report_still_degrades(monkeypatch) -> None:
    harness = Harness(monkeypatch)
    harness.reply_error = LlmUnavailableError()
    harness.report_error = SimulationUnavailableError()
    events = await _events(_prepared())
    assert events[-1] == ("degraded", scene_service.DEGRADED_MESSAGE)


def _stream_with_usage(harness):
    async def stream(system_instruction, contents, usage_sink=None, **_):
        harness.systems.append(system_instruction)
        is_decision = DECISION_MARKER in contents[-1].parts[0].text
        if usage_sink is not None:
            usage_sink.prompt_tokens = 100 if is_decision else 300
            usage_sink.completion_tokens = 10 if is_decision else 50
            usage_sink.cached_tokens = 80 if is_decision else 200
        yield '{"action": "continue_talk"}' if is_decision else LEADER_REPLY

    return stream


async def test_usage_accumulates_over_reply_and_decision_calls(monkeypatch) -> None:
    harness = Harness(monkeypatch)
    monkeypatch.setattr(
        openai_compatible_client, "stream_chat", _stream_with_usage(harness)
    )
    usage = scene_service.SceneUsage()

    _ = [
        event async for event in scene_service.stream_scene_message(_prepared(), usage)
    ]

    assert (usage.prompt_tokens, usage.completion_tokens, usage.cached_tokens) == (
        400,
        60,
        280,
    )


async def test_stream_scene_message_logs_usage_without_prompt_text(
    monkeypatch,
) -> None:
    harness = Harness(monkeypatch)
    monkeypatch.setattr(
        openai_compatible_client, "stream_chat", _stream_with_usage(harness)
    )

    with structlog.testing.capture_logs() as captured:
        await _events(_prepared())

    entries = [item for item in captured if item["event"] == "scene_model_usage"]
    assert len(entries) == 1
    assert entries[0]["scene_type"] == "negotiation"
    assert entries[0]["sequence"] == 1
    assert entries[0]["prompt_tokens"] == 400
    assert entries[0]["completion_tokens"] == 60
    assert entries[0]["cached_tokens"] == 280
    logged = " ".join(str(value) for item in captured for value in item.values())
    assert harness.systems[0] not in logged
    assert "Will you sign a pact?" not in logged
    assert LEADER_REPLY not in logged


async def test_model_calls_get_reasoning_headroom_on_top_of_the_output_limits(
    monkeypatch,
) -> None:
    harness = Harness(monkeypatch)
    limits: list[int] = []
    original = harness._stream

    async def spy(system_instruction, contents, max_output_tokens=None, **kwargs):
        limits.append(max_output_tokens)
        async for piece in original(system_instruction, contents, **kwargs):
            yield piece

    monkeypatch.setattr(openai_compatible_client, "stream_chat", spy)

    await _events(_prepared())

    headroom = settings.scene_reasoning_headroom_tokens
    assert limits == [
        settings.scene_reply_max_output_tokens + headroom,
        settings.scene_decision_max_output_tokens + headroom,
    ]
