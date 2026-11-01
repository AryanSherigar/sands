import os
from pathlib import Path

import pytest
import pytest_asyncio
from app.config import settings
from app.integrations import openai_compatible_client
from app.models.scene import SceneMessageKind, SceneMessageRequest
from app.services import scene_prompt, scene_service
from strategy_contracts.scene_exchange import (
    SceneAction,
    SceneDecision,
    SceneExchangeView,
)
from tests.services.letter_fixtures import GRIEVANCE
from tests.turn.prefix_stability import assert_shared_through

from .budget_loader import REPO_ROOT
from .leak_check import find_leaks
from .report import write_decision_recording, write_report
from .scene_runner import (
    USER_ID,
    FakeSimulation,
    ScenarioResult,
    run_exchange,
    run_scenario,
)
from .scene_scenarios import (
    LETTER_OPTION_IDS,
    MAX_PACT_TURNS,
    ScriptedTurn,
    build_letter_scenarios,
    build_scenarios,
)

pytestmark = pytest.mark.live_scene

ENV_REPORT_PATH = "LIVE_REPORT_PATH"
ENV_DECISIONS_PATH = "LIVE_DECISIONS_PATH"
ENV_SCENARIOS = "LIVE_SCENARIOS"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "reports" / "strategy-live-muse-scenes.md"
DEFAULT_DECISIONS_PATH = REPO_ROOT / ".superpowers" / "live_decisions.json"
INJECTION_SCENARIO = "negotiation_injection"
COOPERATIVE_SCENARIO = "negotiation_cooperative"
EVENT_SCENE_ENDED = "scene_ended"


@pytest_asyncio.fixture(scope="module")
async def scenario_results(live_budget) -> list[ScenarioResult]:
    with pytest.MonkeyPatch.context() as patcher:
        results = [
            await run_scenario(scenario, live_budget, patcher)
            for scenario in _selected_scenarios()
        ]
    write_report(results, Path(os.environ.get(ENV_REPORT_PATH, DEFAULT_REPORT_PATH)))
    write_decision_recording(
        results, Path(os.environ.get(ENV_DECISIONS_PATH, DEFAULT_DECISIONS_PATH))
    )
    return results


def _selected_scenarios():
    chosen = os.environ.get(ENV_SCENARIOS)
    if not chosen:
        return build_scenarios()
    names = set(chosen.split(","))
    return [item for item in build_scenarios() if item.name in names]


def _named(results: list[ScenarioResult], name: str) -> ScenarioResult:
    found = [result for result in results if result.scenario.name == name]
    if not found:
        pytest.skip(f"{name} was not part of this run")
    return found[0]


DECIDING_KINDS = (SceneMessageKind.MESSAGE, SceneMessageKind.SEAL)
INJECTION_SEAL_SCENARIO = "letter_injection"


def _exchanges_of(results, kind: SceneMessageKind):
    return [
        (result, exchange)
        for result in results
        for exchange in result.exchanges
        if exchange.kind is kind
    ]


def test_decisions_parse_or_degrade(scenario_results) -> None:
    exchanges = [
        exchange
        for result in scenario_results
        for exchange in result.exchanges
        if exchange.kind in DECIDING_KINDS
    ]
    assert exchanges
    for exchange in exchanges:
        assert exchange.was_degraded or isinstance(exchange.decision, SceneDecision)


def test_streamed_text_never_contains_a_secret(scenario_results) -> None:
    for result in scenario_results:
        for exchange in result.exchanges:
            findings = find_leaks(exchange.leader_text, result.scenario.secrets)
            assert findings == [], f"{result.scenario.name}: {findings}"


def test_injection_cannot_end_the_scene(scenario_results) -> None:
    injection = _named(scenario_results, INJECTION_SCENARIO)
    for exchange in injection.exchanges:
        decision = exchange.decision
        if decision is not None and decision.action is SceneAction.PROPOSE_TERMS:
            assert (decision.duration_turns or 0) <= MAX_PACT_TURNS
        assert all(name != EVENT_SCENE_ENDED for name, _ in exchange.events)


def test_prefix_is_stable_across_consecutive_exchanges(scenario_results) -> None:
    cooperative = _named(scenario_results, COOPERATIVE_SCENARIO)
    package = cooperative.scenario.package
    first, second = cooperative.exchanges[:2]
    system = scene_prompt.build_system_instruction(package)
    view = SceneExchangeView(
        sequence=1, player_text=first.player_text, leader_text=first.leader_text
    )
    rendered = [
        system + "\n" + "\n".join(part.text for c in contents for part in c.parts)
        for contents in (
            scene_prompt.build_reply_contents([], first.player_text, 6),
            scene_prompt.build_reply_contents([view], second.player_text, 6),
        )
    ]
    assert_shared_through(
        rendered[0], rendered[1], scene_prompt.quote_player(first.player_text)
    )


async def test_model_failure_reports_failure_and_degrades(monkeypatch) -> None:
    scenario = build_scenarios()[0]
    simulation = FakeSimulation(scenario)
    simulation.install(monkeypatch)
    monkeypatch.setattr(settings, "openai_compatible_api_key", "invalid-key")
    monkeypatch.setattr(openai_compatible_client, "_client", None)
    prepared = await scene_service.prepare_exchange(
        scenario.package.scene_id, USER_ID, SceneMessageRequest(text="Hello?")
    )

    events = [e.event async for e in scene_service.stream_scene_message(prepared)]

    assert "degraded" in events
    assert simulation.failure_count == 1
    assert simulation.submissions == []


def test_letter_option_id_is_in_package_or_defaults(scenario_results) -> None:
    seals = _exchanges_of(scenario_results, SceneMessageKind.SEAL)
    letters = [(r, e) for r, e in seals if r.scenario.name.startswith("letter_")]
    if not letters:
        pytest.skip("no letter scenario in this run")
    for result, exchange in letters:
        if exchange.was_degraded:
            continue
        decision = exchange.decision
        is_known_choice = (
            decision.action is SceneAction.CHOOSE_OPTION
            and decision.option_id in LETTER_OPTION_IDS
        )
        if result.scenario.name != INJECTION_SEAL_SCENARIO:
            assert is_known_choice, f"{result.scenario.name}: {decision}"


def test_injecting_seal_cannot_exceed_the_four_options(scenario_results) -> None:
    injection = _named(scenario_results, INJECTION_SEAL_SCENARIO)
    seal = next(e for e in injection.exchanges if e.kind is SceneMessageKind.SEAL)
    if seal.was_degraded:
        pytest.skip("the injected seal degraded; nothing to bound")
    decision = seal.decision
    assert decision.action in (SceneAction.CHOOSE_OPTION, SceneAction.CONTINUE_TALK)
    if decision.action is SceneAction.CHOOSE_OPTION:
        assert decision.option_id in LETTER_OPTION_IDS


def test_the_scribe_draft_never_contains_the_senders_grievance(
    scenario_results,
) -> None:
    scribes = _exchanges_of(scenario_results, SceneMessageKind.SCRIBE)
    if not scribes:
        pytest.skip("no letter scenario in this run")
    for _, exchange in scribes:
        assert GRIEVANCE not in exchange.leader_text


async def test_open_is_not_regenerated_on_reopen(live_budget) -> None:
    scenario = build_letter_scenarios()[0]
    open_turn = ScriptedTurn(SceneMessageKind.OPEN)
    with pytest.MonkeyPatch.context() as patcher:
        simulation = FakeSimulation(scenario)
        simulation.install(patcher)
        first = await run_exchange(simulation, open_turn, live_budget)
        again = await run_exchange(simulation, open_turn, live_budget)
    assert first is not None and again is not None
    assert again.usage.prompt_tokens == 0
    assert again.leader_text == first.leader_text
