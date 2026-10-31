from app.engine.campaign import begin_campaign
from app.models.orders import BesiegeOrder
from app.models.world_events import PhaseName

from tests.engine.diplomacy.builders import queue_npc_order
from tests.engine.sieges.builders import (
    BESIEGER,
    BESIEGER_ARMY,
    SCENARIO,
    TARGET_REGION,
    make_siege_world,
)


def test_a_queued_besiege_order_runs_through_the_real_turn_pipeline() -> None:
    order = BesiegeOrder(
        faction_id=BESIEGER, army_id=BESIEGER_ARMY, target_region_id=TARGET_REGION
    )
    world = queue_npc_order(make_siege_world(), SCENARIO, order)

    result = begin_campaign(world, SCENARIO)

    siege_events = [e for e in result.events if e.phase is PhaseName.SIEGES]
    assert [event.kind for event in siege_events][:2] == [
        "siege_started",
        "siege_progressed",
    ]
    assert [siege.region_id for siege in result.world.sieges] == [TARGET_REGION]
    assert all(event.seq > 0 for event in siege_events)
