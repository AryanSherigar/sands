from app.engine.hashing import canonical_world_json
from app.models.world_events import Overture, PendingNegotiation
from strategy_contracts.overtures import OvertureKind

from tests.models.builders import make_world


def test_ruleset_0_world_omits_overture_keys() -> None:
    world = make_world()
    world.overture_ruleset = 0

    text = canonical_world_json(world)

    assert "overture" not in text


def test_ruleset_1_world_serialises_cooldowns() -> None:
    world = make_world()
    world.overture_ruleset = 1
    world.overture_cooldowns = {"north": 7}

    text = canonical_world_json(world)

    assert '"overture_cooldowns":{"north":7}' in text
    assert '"overture_renewals":[]' in text


def test_pending_negotiation_without_overture_serialises_as_before() -> None:
    pending = PendingNegotiation(
        trigger_id="trigger_a",
        initiator_faction_id="north",
        is_declinable=True,
        cooldown_until_turn=4,
    )

    assert "overture" not in pending.model_dump(mode="json")


def test_pending_negotiation_with_overture_roundtrips() -> None:
    overture = Overture(kind=OvertureKind.CALL_FOR_TALKS, pretext="We would talk.")
    pending = PendingNegotiation(
        trigger_id="overture_north",
        initiator_faction_id="north",
        is_declinable=True,
        cooldown_until_turn=4,
        overture=overture,
    )

    restored = PendingNegotiation.model_validate(pending.model_dump(mode="json"))

    assert restored.overture == overture
