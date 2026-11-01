import pytest
import structlog.testing
from app.exceptions.scene_exceptions import (
    SceneKindMismatchError,
    SceneNotOpenError,
)
from app.exceptions.turn_exceptions import LlmUnavailableError
from app.integrations import openai_compatible_client, simulation_client
from app.models.scene import SceneMessageKind, SceneMessageRequest
from app.services import letter_scene_service, scene_service
from strategy_contracts.scene import SceneStatus, SubmissionStatus
from strategy_contracts.scene_exchange import (
    SceneAction,
    SceneExchangeResult,
    SceneFailureResult,
)
from tests.services.letter_fixtures import (
    GRIEVANCE,
    LETTER_TEXT,
    SCENE_ID,
    USER_ID,
    fetched,
    stored_letter,
)
from tests.services.test_scene_service import _fetched as negotiation_fetched

SEALED = "Our bailiffs will walk the line with yours in spring."
ACK_TEXT = "Then the line is walked."
DECISION_MARKER = "Answer with only a JSON"
WARMER_DECISION = '{"action": "choose_option", "option_id": "letter_warmer"}'


class Harness:
    def __init__(self, monkeypatch, decision_text: str = WARMER_DECISION) -> None:
        self.decision_text = decision_text
        self.systems: list[str] = []
        self.calls = 0
        self.stored: list[str] = []
        self.submissions = []
        self.failure_reports = 0
        self.model_error: Exception | None = None
        self.result = SceneExchangeResult(
            status=SubmissionStatus.ACCEPTED,
            scene_status=SceneStatus.RESOLVED,
            exchanges_remaining=0,
        )
        monkeypatch.setattr(openai_compatible_client, "stream_chat", self._stream)
        monkeypatch.setattr(simulation_client, "store_letter_body", self._store)
        monkeypatch.setattr(simulation_client, "submit_exchange", self._submit)
        monkeypatch.setattr(simulation_client, "report_scene_failure", self._report)

    async def _stream(self, system_instruction, contents, usage_sink=None, **_):
        self.calls += 1
        self.systems.append(system_instruction)
        if self.model_error is not None:
            raise self.model_error
        if usage_sink is not None:
            usage_sink.prompt_tokens, usage_sink.completion_tokens = 100, 20
        last = contents[-1].parts[0].text
        if DECISION_MARKER in last:
            yield self.decision_text
        elif "Write the letter now" in last:
            yield "Valdren, "
            yield "the river fords are watched."
        elif "scribe" in system_instruction.lower():
            yield "Dear Mira, our bailiffs will walk the line."
        else:
            yield ACK_TEXT

    async def _store(self, scene_id, user_id, text):
        self.stored.append(text)
        return SceneExchangeResult(
            status=SubmissionStatus.ACCEPTED,
            scene_status=SceneStatus.OPENED,
            exchanges_remaining=1,
        )

    async def _submit(self, scene_id, user_id, submission):
        self.submissions.append(submission)
        return self.result

    async def _report(self, scene_id, user_id):
        self.failure_reports += 1
        return SceneFailureResult(
            scene_status=SceneStatus.OPENED, failed_attempts=1, attempts_remaining=2
        )


def _serve(monkeypatch, package_fetch) -> None:
    async def fake_fetch(scene_id, user_id):
        return package_fetch

    monkeypatch.setattr(simulation_client, "fetch_scene_package", fake_fetch)


async def _prepare(monkeypatch, package_fetch, **request):
    _serve(monkeypatch, package_fetch)
    return await scene_service.prepare_exchange(
        SCENE_ID, USER_ID, SceneMessageRequest(**request)
    )


async def _events(prepared, usage=None):
    return [
        (event.event, event.data)
        async for event in letter_scene_service.stream_letter_message(prepared, usage)
    ]


def _names(events) -> list[str]:
    return [name for name, _ in events]


def _narration(events) -> str:
    return "".join(data for name, data in events if name == "narration")


async def test_open_streams_the_letter_once_and_stores_it(monkeypatch) -> None:
    harness = Harness(monkeypatch)
    prepared = await _prepare(monkeypatch, fetched(), kind=SceneMessageKind.OPEN)

    events = await _events(prepared)

    assert _narration(events) == "Valdren, the river fords are watched."
    assert harness.stored == ["Valdren, the river fords are watched."]
    assert harness.calls == 1
    assert _names(events)[-1] == "done"
    assert harness.submissions == []


async def test_open_with_a_stored_letter_makes_no_model_call(monkeypatch) -> None:
    harness = Harness(monkeypatch)
    prepared = await _prepare(
        monkeypatch, fetched([stored_letter()]), kind=SceneMessageKind.OPEN
    )

    events = await _events(prepared)

    assert _narration(events) == LETTER_TEXT
    assert (harness.calls, harness.stored) == (0, [])
    assert _names(events)[-1] == "done"


async def test_scribe_does_not_record_an_exchange_or_see_the_brief(
    monkeypatch,
) -> None:
    harness = Harness(monkeypatch)
    prepared = await _prepare(
        monkeypatch,
        fetched([stored_letter()]),
        kind=SceneMessageKind.SCRIBE,
        text="Make it firmer",
        current_draft="Dear Mira, we hear you.",
    )

    events = await _events(prepared)

    assert _narration(events) == "Dear Mira, our bailiffs will walk the line."
    assert (harness.stored, harness.submissions) == ([], [])
    assert GRIEVANCE not in harness.systems[0]


async def test_seal_submits_sequence_two_with_a_choose_option_decision(
    monkeypatch,
) -> None:
    harness = Harness(monkeypatch)
    prepared = await _prepare(
        monkeypatch,
        fetched([stored_letter()]),
        kind=SceneMessageKind.SEAL,
        text=SEALED,
    )

    events = await _events(prepared)

    submission = harness.submissions[0]
    assert submission.sequence == 2
    assert submission.player_text == SEALED
    assert submission.leader_text == ACK_TEXT
    assert submission.decision.action is SceneAction.CHOOSE_OPTION
    assert submission.decision.option_id == "letter_warmer"
    assert _narration(events) == ACK_TEXT
    assert "scene_ended" in _names(events)
    assert _names(events)[-1] == "done"


async def test_seal_forwards_an_unknown_option_and_the_scene_does_not_crash(
    monkeypatch,
) -> None:
    harness = Harness(
        monkeypatch, '{"action": "choose_option", "option_id": "gift_gold"}'
    )
    harness.result = SceneExchangeResult(
        status=SubmissionStatus.ACCEPTED,
        scene_status=SceneStatus.DEFAULTED,
        exchanges_remaining=0,
        reason="not_allowed",
    )
    prepared = await _prepare(
        monkeypatch,
        fetched([stored_letter()]),
        kind=SceneMessageKind.SEAL,
        text=SEALED,
    )

    events = await _events(prepared)

    assert harness.submissions[0].decision.option_id == "gift_gold"
    assert "scene_ended" in _names(events)


async def test_seal_with_an_unparseable_decision_forwards_continue_talk(
    monkeypatch,
) -> None:
    harness = Harness(monkeypatch, "I think the queen is pleased.")
    prepared = await _prepare(
        monkeypatch,
        fetched([stored_letter()]),
        kind=SceneMessageKind.SEAL,
        text=SEALED,
    )

    await _events(prepared)

    assert harness.submissions[0].decision.action is SceneAction.CONTINUE_TALK


async def test_a_failed_open_degrades_and_counts_a_scene_failure(monkeypatch) -> None:
    harness = Harness(monkeypatch)
    harness.model_error = LlmUnavailableError()
    prepared = await _prepare(monkeypatch, fetched(), kind=SceneMessageKind.OPEN)

    events = await _events(prepared)

    assert _names(events) == ["degraded"]
    assert harness.failure_reports == 1
    assert harness.stored == []


async def test_a_failed_scribe_degrades_without_counting_a_scene_failure(
    monkeypatch,
) -> None:
    harness = Harness(monkeypatch)
    harness.model_error = LlmUnavailableError()
    prepared = await _prepare(
        monkeypatch,
        fetched([stored_letter()]),
        kind=SceneMessageKind.SCRIBE,
        text="firmer",
        current_draft="draft",
    )

    events = await _events(prepared)

    assert _names(events) == ["degraded"]
    assert harness.failure_reports == 0


async def test_letter_usage_is_logged_without_prompt_text(monkeypatch) -> None:
    Harness(monkeypatch)
    prepared = await _prepare(monkeypatch, fetched(), kind=SceneMessageKind.OPEN)

    with structlog.testing.capture_logs() as captured:
        await _events(prepared)

    entries = [item for item in captured if item["event"] == "scene_model_usage"]
    assert len(entries) == 1
    assert entries[0]["scene_type"] == "letter"
    assert entries[0]["prompt_tokens"] == 100
    assert "river fords" not in str(captured)


async def test_sealing_before_the_letter_is_opened_is_refused(monkeypatch) -> None:
    Harness(monkeypatch)
    with pytest.raises(SceneKindMismatchError):
        await _prepare(monkeypatch, fetched(), kind=SceneMessageKind.SEAL, text=SEALED)


async def test_a_plain_message_to_a_letter_is_refused(monkeypatch) -> None:
    Harness(monkeypatch)
    with pytest.raises(SceneKindMismatchError):
        await _prepare(monkeypatch, fetched([stored_letter()]), text="hello")


async def test_letter_kinds_are_refused_on_a_negotiation(monkeypatch) -> None:
    Harness(monkeypatch)
    with pytest.raises(SceneKindMismatchError):
        await _prepare(monkeypatch, negotiation_fetched(), kind=SceneMessageKind.OPEN)


async def test_sealing_a_finished_letter_is_refused(monkeypatch) -> None:
    Harness(monkeypatch)
    with pytest.raises(SceneNotOpenError):
        await _prepare(
            monkeypatch,
            fetched([stored_letter()], status=SceneStatus.RESOLVED),
            kind=SceneMessageKind.SEAL,
            text=SEALED,
        )
