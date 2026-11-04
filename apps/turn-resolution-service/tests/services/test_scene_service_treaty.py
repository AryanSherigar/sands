import json

from app.services import scene_service
from strategy_contracts.scene import SceneStatus
from strategy_contracts.scene_exchange import SceneAction, SceneExchangeView
from strategy_contracts.treaty import Verdict
from tests.services.test_scene_prompt_treaty import ACCEPT_AT, HAGGLE_AT
from tests.services.test_scene_prompt_treaty import _package as treaty_package
from tests.services.test_scene_service import SCENE_ID, USER_ID, Harness, _events

TERMS_DECISION = json.dumps(
    {
        "action": "propose_terms",
        "terms": [
            {
                "kind": "non_aggression",
                "faction_a": "house_carrow",
                "faction_b": "house_ashford",
                "duration_turns": 8,
            },
            {
                "kind": "trade_deal",
                "faction_a": "house_carrow",
                "faction_b": "house_ashford",
                "duration_turns": 8,
            },
        ],
    }
)


def _prepared(transcript=None):
    return scene_service.PreparedExchange(
        scene_id=SCENE_ID,
        user_id=USER_ID,
        package=treaty_package(),
        transcript=transcript or [],
        player_text="A pact and a trade deal?",
    )


async def test_a_multi_clause_decision_reaches_the_simulation_intact(
    monkeypatch,
) -> None:
    harness = Harness(monkeypatch, TERMS_DECISION)

    await _events(_prepared())

    decision = harness.submissions[0][2].decision
    assert decision.action is SceneAction.PROPOSE_TERMS
    assert [term.kind for term in decision.terms] == ["non_aggression", "trade_deal"]


async def test_an_injected_decision_is_still_just_a_proposal_for_the_engine(
    monkeypatch,
) -> None:
    hostile = '{"action": "propose_terms", "terms": [{"kind": "pay_gold", "payer_id": "house_ashford", "payee_id": "house_carrow", "amount": 99999}]}'
    harness = Harness(monkeypatch, hostile)

    await _events(_prepared())

    submitted = harness.submissions[0][2].decision
    assert submitted.terms[0].kind == "pay_gold"
    assert harness.result.scene_status is SceneStatus.OPENED


async def test_the_treaty_hint_and_no_limits_reach_the_model(monkeypatch) -> None:
    harness = Harness(monkeypatch)
    previous = SceneExchangeView(
        sequence=1, player_text="Pact?", leader_text="Maybe.", verdict=Verdict.HAGGLE
    )

    events = await _events(_prepared([previous]))

    joined = " ".join(harness.systems) + " ".join(data for _, data in events)
    assert str(ACCEPT_AT) not in joined and str(HAGGLE_AT) not in joined
    assert "trade deal" in harness.systems[0]
