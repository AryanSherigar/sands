from app.engine.hashing import canonical_world_json
from app.engine.ordering import canonicalize_lists
from app.models.battle_command import Command
from app.models.orders import (
    AnnexVassalOrder,
    AnswerDemandOrder,
    DemandFromVassalOrder,
    GrantConsentOrder,
    ReleaseVassalOrder,
)
from app.models.world_alliance import CallKind, CallToArmsState
from app.models.world_diplomacy import WarSide
from app.models.world_state import CURRENT_VASSAL_RULESET
from app.models.world_vassal import DemandState
from pydantic import TypeAdapter
from strategy_contracts.vassal import (
    ConsentAction,
    DemandKind,
    DemandReply,
)

from tests.models.builders import make_world


def _call(kind: CallKind = CallKind.ALLIANCE) -> CallToArmsState:
    return CallToArmsState(
        id="call_1",
        alliance_id="commitment_1",
        war_id="war_1",
        caller_id="aa",
        ally_id="cc",
        side=WarSide.ATTACKER,
        issued_turn=3,
        deadline_turn=4,
        is_defensive=False,
        kind=kind,
    )


def _demand(demand_id: str) -> DemandState:
    return DemandState(
        id=demand_id,
        vassalage_id="commitment_1",
        overlord_id="aa",
        vassal_id="bb",
        kind=DemandKind.TRIBUTE,
        amount=60,
        granted=30,
        issued_turn=2,
        deadline_turn=3,
    )


def test_new_world_constant_is_one() -> None:
    assert CURRENT_VASSAL_RULESET == 1


def test_legacy_world_dump_has_no_vassal_keys() -> None:
    text = canonical_world_json(make_world())

    assert "vassal_ruleset" not in text
    assert '"vassal"' not in text


def test_ruleset_one_world_carries_vassal_fields() -> None:
    world = make_world()
    world.vassal_ruleset = CURRENT_VASSAL_RULESET

    text = canonical_world_json(world)

    assert '"vassal_ruleset":1' in text
    assert '"vassal":{' in text


def test_alliance_call_dump_omits_kind() -> None:
    assert "kind" not in _call().model_dump(mode="json")


def test_levy_call_dump_keeps_kind() -> None:
    assert _call(CallKind.LEVY).model_dump(mode="json")["kind"] == "levy"


def test_demands_sorted_by_id_in_canonical_form() -> None:
    world = make_world()
    world.vassal_ruleset = CURRENT_VASSAL_RULESET
    world.vassal.demands = [_demand("demand_2"), _demand("demand_1")]

    canonicalize_lists(world)

    assert [item.id for item in world.vassal.demands] == ["demand_1", "demand_2"]


def test_order_models_round_trip_in_command_union() -> None:
    adapter = TypeAdapter(Command)
    orders = [
        DemandFromVassalOrder(
            faction_id="aa",
            vassalage_id="commitment_1",
            demand_kind=DemandKind.TRIBUTE,
            amount=60,
        ),
        AnswerDemandOrder(
            faction_id="bb", demand_id="demand_1", reply=DemandReply.REFUSE
        ),
        GrantConsentOrder(
            faction_id="aa",
            vassalage_id="commitment_1",
            action=ConsentAction.DECLARE_WAR,
            target_faction_id="cc",
        ),
        ReleaseVassalOrder(faction_id="aa", vassalage_id="commitment_1"),
        AnnexVassalOrder(faction_id="aa", vassalage_id="commitment_1"),
    ]

    for order in orders:
        assert adapter.validate_python(order.model_dump(mode="json")) == order
