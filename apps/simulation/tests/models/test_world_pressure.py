from app.engine.hashing import canonical_world_json
from app.engine.ordering import canonicalize_lists
from app.models.world_pressure import MediationOffer, PressureState, SubsidyState
from app.models.world_state import CURRENT_PRESSURE_RULESET

from tests.models.builders import make_world


def test_legacy_world_serializes_without_pressure_keys() -> None:
    text = canonical_world_json(make_world())

    assert "pressure_ruleset" not in text
    assert '"pressure"' not in text


def test_ruleset_one_world_carries_pressure_fields() -> None:
    world = make_world()
    world.pressure_ruleset = CURRENT_PRESSURE_RULESET

    text = canonical_world_json(world)

    assert '"pressure_ruleset":1' in text
    assert '"pressure":{' in text


def test_pressure_state_defaults_are_empty() -> None:
    state = PressureState()

    assert state.stalemate_turns == {}
    assert state.humiliation == {}
    assert state.devastation == {}
    assert state.shocks == []
    assert state.mediation_offers == []
    assert state.subsidies == []
    assert state.rumors == []


def test_pressure_lists_are_sorted_by_canonicalize_lists() -> None:
    world = make_world()
    world.pressure.mediation_offers = [
        MediationOffer(
            id="med_2", mediator_id="house_ashford", war_id="war_1", expires_turn=3
        ),
        MediationOffer(
            id="med_1", mediator_id="house_ashford", war_id="war_2", expires_turn=3
        ),
    ]
    world.pressure.subsidies = [
        SubsidyState(
            id="sub_2",
            payer_id="house_ashford",
            receiver_id="house_carrow",
            war_id="war_1",
            expires_turn=3,
        ),
        SubsidyState(
            id="sub_1",
            payer_id="house_ashford",
            receiver_id="house_carrow",
            war_id="war_1",
            expires_turn=3,
        ),
    ]

    canonicalize_lists(world)

    assert [item.id for item in world.pressure.mediation_offers] == ["med_1", "med_2"]
    assert [item.id for item in world.pressure.subsidies] == ["sub_1", "sub_2"]
