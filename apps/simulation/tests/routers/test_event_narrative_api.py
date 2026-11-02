from uuid import UUID, uuid4

from app.repositories.event_delivery_repo import EventDeliveryRepo
from httpx import AsyncClient
from psycopg import AsyncConnection
from strategy_contracts.events import (
    EventNarrativeBriefing,
    EventNarrativePayload,
)
from tests.services.art_helpers import seed_campaign

HEADERS = {"X-Internal-Service-Token": "internal"}


def _briefing(playthrough_id: UUID, event_id: str) -> EventNarrativeBriefing:
    return EventNarrativeBriefing(
        playthrough_id=playthrough_id,
        event_id=event_id,
        template_id="tax_grievance",
        template_name="Tax grievance",
        subject_name="Dunmere Vale",
        tier=1,
        cause_description="unrest is 45",
        ruler_name="Aldric Vane",
        ruler_traits=["stern"],
        season_year="Spring 1001",
        choices=[{"id": "grant_relief", "label": "Grant tax relief"}],
    )


def _payload() -> EventNarrativePayload:
    return EventNarrativePayload(
        body_prose="The town bailiffs gathered quietly before the gate.",
        cause_quote="We have given until our stores are empty.",
        character_name="Elder Brandon",
        character_title="Guild Reeve",
        disposition="Resentful",
    )


def _internal_path(identity: UUID, event_id: str, action: str) -> str:
    return f"/internal/v1/playthroughs/{identity}/events/{event_id}/{action}"


async def test_missing_service_token_is_rejected(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    identity = await seed_campaign(db_connection)
    path = _internal_path(identity, "pe_1", "claim")
    response = await api.post(path, json={"claim_id": str(uuid4())})
    assert response.status_code in (401, 403)


async def test_unknown_event_claim_returns_409(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    identity = await seed_campaign(db_connection)
    path = _internal_path(identity, "pe_missing", "claim")
    response = await api.post(path, json={"claim_id": str(uuid4())}, headers=HEADERS)
    assert response.status_code == 409


async def test_claim_complete_round_trip_and_public_read(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    identity = await seed_campaign(db_connection)
    repo = EventDeliveryRepo()
    briefing = _briefing(identity, "pe_1")
    await repo.insert_pending(db_connection, identity, "pe_1", 1, briefing)

    claim_res = await api.post(
        _internal_path(identity, "pe_1", "claim"),
        json={"claim_id": str(uuid4())},
        headers=HEADERS,
    )
    assert claim_res.status_code == 200
    claim_body = claim_res.json()
    assert "lease_token" in claim_body
    assert claim_body["briefing"]["template_id"] == "tax_grievance"

    second_claim = await api.post(
        _internal_path(identity, "pe_1", "claim"),
        json={"claim_id": str(uuid4())},
        headers=HEADERS,
    )
    assert second_claim.status_code == 409

    bad_complete = await api.post(
        _internal_path(identity, "pe_1", "complete"),
        json={
            "lease_token": str(uuid4()),
            "narration": _payload().model_dump(mode="json"),
        },
        headers=HEADERS,
    )
    assert bad_complete.status_code == 409

    complete_res = await api.post(
        _internal_path(identity, "pe_1", "complete"),
        json={
            "lease_token": claim_body["lease_token"],
            "narration": _payload().model_dump(mode="json"),
        },
        headers=HEADERS,
    )
    assert complete_res.status_code == 200
    assert complete_res.json() == {"status": "completed"}

    public_res = await api.get(f"/v1/playthroughs/{identity}/events/pe_1/narrative")
    assert public_res.status_code == 200
    public_body = public_res.json()
    assert public_body["event_id"] == "pe_1"
    assert public_body["status"] == "completed"
    assert public_body["narration"]["character_name"] == "Elder Brandon"


async def test_fail_route_records_failure(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    identity = await seed_campaign(db_connection)
    repo = EventDeliveryRepo()
    briefing = _briefing(identity, "pe_2")
    await repo.insert_pending(db_connection, identity, "pe_2", 1, briefing)

    claim_res = await api.post(
        _internal_path(identity, "pe_2", "claim"),
        json={"claim_id": str(uuid4())},
        headers=HEADERS,
    )
    assert claim_res.status_code == 200
    lease_token = claim_res.json()["lease_token"]

    fail_res = await api.post(
        _internal_path(identity, "pe_2", "fail"),
        json={"lease_token": lease_token, "error_code": "model_error"},
        headers=HEADERS,
    )
    assert fail_res.status_code == 200
    assert fail_res.json() == {"status": "failed"}

    public_res = await api.get(f"/v1/playthroughs/{identity}/events/pe_2/narrative")
    assert public_res.status_code == 200
    public_body = public_res.json()
    assert public_body["status"] == "failed"
    assert public_body["narration"] is None


async def test_public_narrative_not_found(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    identity = await seed_campaign(db_connection)
    res = await api.get(f"/v1/playthroughs/{identity}/events/pe_none/narrative")
    assert res.status_code == 404


def test_project_pending_events_attaches_narratives() -> None:
    from app.models.world_events import PendingEvent
    from app.services.event_projection import project_pending_events
    from strategy_contracts.conditions import ConditionScope
    from tests.engine.events.builders import make_disaster_world, make_scenario

    world = make_disaster_world()
    scenario = make_scenario()
    region_id = next(iter(world.regions))
    pending = PendingEvent(
        id="pe_1",
        template_id=scenario.events[0].id,
        choice_ids=[scenario.events[0].choices[0].id],
        subject_kind=ConditionScope.REGION,
        subject_id=region_id,
        subject_name="Test Region",
        tier=1,
        created_turn=1,
        deadline_turn=3,
        cause_key="test_cause",
    )
    world.pending_events.append(pending)
    payload = _payload()

    views_none = project_pending_events(world, scenario, "house_carrow")
    view_item = next(v for v in views_none if v.id == "pe_1")
    assert view_item.narrative is None

    views_with = project_pending_events(
        world, scenario, "house_carrow", narratives={"pe_1": payload}
    )
    view_item_with = next(v for v in views_with if v.id == "pe_1")
    assert view_item_with.narrative == payload


def test_events_phase_records_pending_event_deliveries() -> None:
    from tests.engine.events.builders import (
        make_disaster_world,
        make_scenario,
        run_events,
    )

    world = make_disaster_world(month=8)
    scenario = make_scenario()
    after, _ = run_events(world, scenario)
    assert len(after.pending_event_deliveries) > 0
    briefing = after.pending_event_deliveries[0]
    assert briefing.event_id == "event_1"
    assert briefing.template_id == "bad_harvest"
    assert briefing.playthrough_id == world.playthrough_id
    assert briefing.ruler_name == world.ruler.name
