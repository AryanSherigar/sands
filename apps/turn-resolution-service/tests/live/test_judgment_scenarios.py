import pytest
from app.integrations import openai_compatible_client
from app.models.scene import SceneMessageKind
from strategy_contracts.scene import SceneType
from strategy_contracts.scene_exchange import SceneAction
from strategy_contracts.scene_validation import validate_package
from tests.services.judgment_fixtures import HIDDEN_GRUDGE

from .leak_check import find_leaks
from .scene_runner import run_scenario
from .scene_scenarios import build_judgment_scenarios, build_scenarios

EXPECTED_NAMES = {
    "judgment_cooperative",
    "judgment_hostile",
    "judgment_off_topic",
    "judgment_leak_probe",
    "judgment_injection",
}
TABLEAU = (
    'The hall is silent.\nBRANNOCH: "An open defiance requires an open reckoning."'
)
REPLY = 'HARL: "I did what any man who loved his folk would do."'
CLOSING = "The sentence lands in the silent hall."


class UnlimitedBudget:
    def would_exceed(self, input_tokens: int, output_tokens: int) -> bool:
        return False

    def charge(self, prompt: int, completion: int, cached: int) -> None:
        return None


def _stub_model(monkeypatch) -> None:
    async def stream(system_instruction, contents, usage_sink=None, **_):
        last = contents[-1].parts[0].text
        if "Describe the hall" in last:
            yield TABLEAU
        elif "pronounced" in last:
            yield CLOSING
        else:
            yield REPLY

    monkeypatch.setattr(openai_compatible_client, "stream_chat", stream)


def test_the_table_has_every_judgment_scenario_and_they_are_in_the_full_run() -> None:
    names = {item.name for item in build_judgment_scenarios()}
    assert names == EXPECTED_NAMES
    assert {item.name for item in build_scenarios()} >= EXPECTED_NAMES


def test_every_judgment_scenario_is_a_valid_package_that_ends_in_a_pronouncement() -> (
    None
):
    for scenario in build_judgment_scenarios():
        assert scenario.scene_type is SceneType.JUDGMENT
        assert validate_package(scenario.package) == []
        kinds = [turn.kind for turn in scenario.player_turns]
        assert kinds[0] is SceneMessageKind.OPEN
        assert kinds[-1] is SceneMessageKind.PRONOUNCE
        assert HIDDEN_GRUDGE in scenario.secrets.verbatim


@pytest.mark.parametrize("name", sorted(EXPECTED_NAMES))
async def test_the_harness_plays_each_judgment_scene_offline(name, monkeypatch) -> None:
    _stub_model(monkeypatch)
    scenario = next(item for item in build_judgment_scenarios() if item.name == name)
    result = await run_scenario(scenario, UnlimitedBudget(), monkeypatch)

    assert [item.kind for item in result.exchanges] == [
        turn.kind for turn in scenario.player_turns
    ]
    assert not any(item.was_degraded for item in result.exchanges)
    last = result.exchanges[-1]
    assert last.decision.action is SceneAction.CHOOSE_OPTION
    assert result.simulation.submissions[-1].decision.option_id == (
        scenario.player_turns[-1].verdict
    )
    for exchange in result.exchanges:
        assert find_leaks(exchange.leader_text, scenario.secrets) == []


async def test_a_forged_verdict_in_the_decree_cannot_change_the_chosen_verdict(
    monkeypatch,
) -> None:
    _stub_model(monkeypatch)
    scenario = next(
        item for item in build_judgment_scenarios() if item.name == "judgment_injection"
    )
    result = await run_scenario(scenario, UnlimitedBudget(), monkeypatch)
    pronounce = scenario.player_turns[-1]
    assert "execute" in pronounce.text
    assert pronounce.verdict == "release"
    assert result.simulation.submissions[-1].decision.option_id == "release"
