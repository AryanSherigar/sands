from uuid import UUID

import pytest
from app.models.api_internal import InitWorldRequest, InitWorldResponse
from app.models.api_orders import (
    CancelOrderResponse,
    OrderFlag,
    QueueOrderRequest,
    QueueOrderResponse,
)
from app.models.api_scenes import SceneStatusResponse
from app.models.api_turn import (
    BattlePlanRequest,
    EndTurnResponse,
    EventChoiceRequest,
    ReportLine,
    TurnReport,
)
from app.models.world_events import EventCause, TurnStatus
from app.models.world_player import PlayerRuler
from pydantic import ValidationError
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.scene import SceneStatus, SceneType

from tests.models.test_orders import ORDER_EXAMPLES

PLAYTHROUGH_ID = UUID("33333333-3333-3333-3333-333333333333")
OWNER_ID = UUID("55555555-5555-5555-5555-555555555555")


def _ruler() -> PlayerRuler:
    return PlayerRuler(
        name="Valdren",
        trait_ids=["honorable", "cautious"],
        ambition_ids=["ambition_peace"],
    )


@pytest.mark.parametrize("order", ORDER_EXAMPLES, ids=lambda o: str(o["kind"]))
def test_queue_request_accepts_each_order_kind(order: dict[str, object]) -> None:
    request = QueueOrderRequest.model_validate({"order": order})
    assert QueueOrderRequest.model_validate_json(request.model_dump_json()) == request


def test_over_budget_response_round_trips() -> None:
    response = QueueOrderResponse(
        flag=OrderFlag.OVER_BUDGET, reason="no orders left", orders_remaining=0
    )
    assert response.queued is None
    assert (
        QueueOrderResponse.model_validate_json(response.model_dump_json()) == response
    )


def test_init_request_accepts_the_example_scenario() -> None:
    request = InitWorldRequest(
        playthrough_id=PLAYTHROUGH_ID,
        owner_user_id=OWNER_ID,
        scenario=load_three_crowns(),
        ruler=_ruler(),
        seed=42,
    )
    assert InitWorldRequest.model_validate_json(request.model_dump_json()) == request


def test_float_seed_is_rejected() -> None:
    with pytest.raises(ValidationError):
        InitWorldRequest.model_validate(
            {
                "playthrough_id": str(PLAYTHROUGH_ID),
                "owner_user_id": str(OWNER_ID),
                "scenario": load_three_crowns().model_dump(mode="json"),
                "ruler": _ruler().model_dump(),
                "seed": 1.5,
            }
        )


def test_small_response_models_round_trip() -> None:
    models = [
        InitWorldResponse(playthrough_id=PLAYTHROUGH_ID, world_hash="ab" * 32, turn=0),
        CancelOrderResponse(refunded=1, orders_remaining=4),
        EndTurnResponse(status=TurnStatus.RESOLVED, turn=2),
        TurnReport(
            turn=2,
            lines=[
                ReportLine(
                    text_key="tax_collected", cause=EventCause(summary_key="tax")
                )
            ],
        ),
        EventChoiceRequest(choice_id="pay_bribe"),
        BattlePlanRequest(
            formation={"center": 60, "flanks": 30, "reserve": 10}, tactic="ambush"
        ),
        SceneStatusResponse(
            scene_id=PLAYTHROUGH_ID,
            scene_type=SceneType.NEGOTIATION,
            status=SceneStatus.OPENED,
            turn=2,
        ),
    ]
    for model in models:
        assert type(model).model_validate_json(model.model_dump_json()) == model
