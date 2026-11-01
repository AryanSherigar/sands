from typing import get_args

import pytest
from app.models.orders import Order, QueuedOrder
from pydantic import TypeAdapter, ValidationError
from strategy_contracts.enums import OrderKind, RouteStyle

ORDER_ADAPTER = TypeAdapter(Order)

ORDER_EXAMPLES: list[dict[str, object]] = [
    {"kind": "move_army", "faction_id": "aa", "army_id": "ar", "to_region_id": "rr"},
    {"kind": "halt_army", "faction_id": "aa", "army_id": "ar"},
    {"kind": "attack", "faction_id": "aa", "army_id": "ar", "target_region_id": "rr"},
    {
        "kind": "besiege",
        "faction_id": "aa",
        "army_id": "ar",
        "target_region_id": "rr",
    },
    {
        "kind": "raise_army",
        "faction_id": "aa",
        "region_id": "rr",
        "troops": {"infantry": 50},
    },
    {"kind": "disband_army", "faction_id": "aa", "army_id": "ar"},
    {
        "kind": "merge_armies",
        "faction_id": "aa",
        "army_ids": ["a1", "a2"],
        "into_army_id": "a1",
    },
    {
        "kind": "split_army",
        "faction_id": "aa",
        "army_id": "ar",
        "troops": {"cavalry": 10},
    },
    {"kind": "set_pay", "faction_id": "aa", "army_id": "ar", "pay_level": "reduced"},
    {"kind": "set_tax_rate", "faction_id": "aa", "tax_rate": "high"},
    {"kind": "take_loan", "faction_id": "aa", "amount": 100},
    {
        "kind": "build_improvement",
        "faction_id": "aa",
        "region_id": "rr",
        "improvement_kind": "fort",
    },
    {
        "kind": "diplomatic_play",
        "faction_id": "aa",
        "target_faction_id": "bb",
        "demands": [],
    },
    {
        "kind": "propose_agreement",
        "faction_id": "aa",
        "target_faction_id": "bb",
        "agreement": "truce",
    },
    {"kind": "send_envoy", "faction_id": "aa", "target_faction_id": "bb"},
    {
        "kind": "handle_prisoner",
        "faction_id": "aa",
        "prisoner_id": "pr",
        "action": "ransom",
    },
    {
        "kind": "answer_call",
        "faction_id": "aa",
        "call_id": "call_1",
        "is_joining": True,
    },
    {"kind": "denounce_alliance", "faction_id": "aa", "alliance_id": "commitment_1"},
    {
        "kind": "appease_coalition",
        "faction_id": "aa",
        "member_id": "bb",
        "offer": {"kind": "gold", "amount": 5},
    },
    {
        "kind": "appease_coalition",
        "faction_id": "aa",
        "member_id": "bb",
        "offer": {"kind": "pact", "duration_turns": 4},
    },
    {
        "kind": "appease_coalition",
        "faction_id": "aa",
        "member_id": "bb",
        "offer": {"kind": "claim_cession", "region_id": "rr"},
    },
]


@pytest.mark.parametrize("payload", ORDER_EXAMPLES, ids=lambda p: str(p["kind"]))
def test_each_order_kind_parses(payload: dict[str, object]) -> None:
    order = ORDER_ADAPTER.validate_python(payload)
    assert ORDER_ADAPTER.validate_json(ORDER_ADAPTER.dump_json(order)) == order


def test_union_covers_every_order_kind() -> None:
    union_members = get_args(get_args(Order)[0])
    kinds = {member.model_fields["kind"].default for member in union_members}
    assert kinds == {kind.value for kind in OrderKind}


def test_unknown_kind_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ORDER_ADAPTER.validate_python({"kind": "teleport", "faction_id": "aa"})


def test_merge_needs_two_armies() -> None:
    with pytest.raises(ValidationError):
        ORDER_ADAPTER.validate_python(
            {
                "kind": "merge_armies",
                "faction_id": "aa",
                "army_ids": ["a1"],
                "into_army_id": "a1",
            }
        )


def test_negative_troops_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ORDER_ADAPTER.validate_python(
            {
                "kind": "raise_army",
                "faction_id": "aa",
                "region_id": "rr",
                "troops": {"infantry": -5},
            }
        )


def test_float_loan_amount_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ORDER_ADAPTER.validate_python(
            {"kind": "take_loan", "faction_id": "aa", "amount": 1.5}
        )


def test_queued_order_round_trips() -> None:
    queued = QueuedOrder(
        id="o1",
        order=ORDER_ADAPTER.validate_python(ORDER_EXAMPLES[0]),
        cost=1,
        queued_turn=2,
    )
    assert QueuedOrder.model_validate_json(queued.model_dump_json()) == queued


def _move(**extra: object) -> dict[str, object]:
    return {
        "kind": "move_army",
        "faction_id": "aa",
        "army_id": "ar",
        "to_region_id": "rr",
    } | extra


def test_a_plain_move_order_defaults_to_the_fastest_unconstrained_route() -> None:
    order = ORDER_ADAPTER.validate_python(_move())
    assert order.route_style is RouteStyle.FASTEST
    assert order.via_region_ids == []
    assert order.avoid_region_ids == []


def test_route_choices_round_trip() -> None:
    order = ORDER_ADAPTER.validate_python(
        _move(
            route_style="safest", via_region_ids=["v1"], avoid_region_ids=["x1", "x2"]
        )
    )
    assert ORDER_ADAPTER.validate_json(ORDER_ADAPTER.dump_json(order)) == order


@pytest.mark.parametrize("style", ["fastest", "safest", "roads"])
def test_each_route_style_parses(style: str) -> None:
    assert (
        ORDER_ADAPTER.validate_python(_move(route_style=style)).route_style.value
        == style
    )


def test_unknown_route_style_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ORDER_ADAPTER.validate_python(_move(route_style="scenic"))


def test_via_regions_are_capped_at_three() -> None:
    ORDER_ADAPTER.validate_python(_move(via_region_ids=["v1", "v2", "v3"]))
    with pytest.raises(ValidationError):
        ORDER_ADAPTER.validate_python(_move(via_region_ids=["v1", "v2", "v3", "v4"]))


def test_avoid_regions_are_capped_at_five() -> None:
    ORDER_ADAPTER.validate_python(_move(avoid_region_ids=[f"x{n}" for n in range(5)]))
    with pytest.raises(ValidationError):
        ORDER_ADAPTER.validate_python(
            _move(avoid_region_ids=[f"x{n}" for n in range(6)])
        )


@pytest.mark.parametrize("field", ["via_region_ids", "avoid_region_ids"])
def test_duplicate_regions_in_a_list_are_rejected(field: str) -> None:
    with pytest.raises(ValidationError):
        ORDER_ADAPTER.validate_python(_move(**{field: ["r1", "r1"]}))


def test_a_region_cannot_be_both_via_and_avoid() -> None:
    with pytest.raises(ValidationError):
        ORDER_ADAPTER.validate_python(
            _move(via_region_ids=["r1"], avoid_region_ids=["r1"])
        )


def test_invalid_region_ids_in_route_lists_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ORDER_ADAPTER.validate_python(_move(via_region_ids=["Not An Id"]))


def test_besiege_order_requires_a_target_region() -> None:
    with pytest.raises(ValidationError):
        ORDER_ADAPTER.validate_python(
            {"kind": "besiege", "faction_id": "aa", "army_id": "ar"}
        )
