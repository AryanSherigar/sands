from uuid import UUID, uuid4

from app.engine.world_document import world_from_document
from app.repositories import summary_delivery_repo, world_state_repo
from app.services.campaign_service import CampaignService
from app.services.summary_materialization import briefing_hash
from psycopg import AsyncConnection
from strategy_contracts.summary import SummaryBriefing, SummaryFact
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.test_campaign_service import initialization

EVENT_ID = "evt_grievance_1"
UPRISING_ID = "upr_1"
FOREIGN_USER_ID = UUID("66666666-6666-6666-6666-666666666666")


async def seed_campaign(connection: AsyncConnection) -> UUID:
    request = initialization()
    await CampaignService(connection).initialize(request)
    await connection.commit()
    return request.playthrough_id


async def _save_document(
    connection: AsyncConnection, identity: UUID, document: dict[str, object]
) -> None:
    row = await world_state_repo.get_world_state(connection, identity)
    assert row is not None
    await world_state_repo.update_world_state(
        connection,
        identity,
        row.row_version,
        row.schema_version,
        row.turn,
        row.world_hash,
        document,
    )
    await connection.commit()


async def add_pending_event(connection: AsyncConnection, identity: UUID) -> None:
    row = await world_state_repo.get_world_state(connection, identity)
    assert row is not None
    world = world_from_document(row.document)
    home = next(r.id for r in world.regions.values() if r.owner_id == "house_carrow")
    document = dict(row.document)
    document["pending_events"] = [
        {
            "id": EVENT_ID,
            "template_id": "tax_grievance",
            "choice_ids": ["ease_taxes"],
            "subject_kind": "region",
            "subject_id": home,
            "subject_name": "Carrow Fields",
            "tier": 1,
            "created_turn": 0,
            "deadline_turn": 3,
            "cause_key": "tax_grievance",
            "cause_inputs": {"region_unrest": 70},
        }
    ]
    await _save_document(connection, identity, document)


async def remove_pending_events(connection: AsyncConnection, identity: UUID) -> None:
    row = await world_state_repo.get_world_state(connection, identity)
    assert row is not None
    document = dict(row.document)
    document["pending_events"] = []
    await _save_document(connection, identity, document)


async def add_uprising(connection: AsyncConnection, identity: UUID) -> None:
    row = await world_state_repo.get_world_state(connection, identity)
    assert row is not None
    world = world_from_document(row.document)
    home = next(r.id for r in world.regions.values() if r.owner_id == "house_carrow")
    document = dict(row.document)
    document["uprisings"] = [
        {
            "id": UPRISING_ID,
            "region_id": home,
            "faction_id": "house_carrow",
            "started_turn": 0,
            "trigger_unrest": 80,
            "income_penalty_percent": 10,
            "manpower_penalty_percent": 10,
            "supply_penalty_percent": 10,
        }
    ]
    await _save_document(connection, identity, document)


async def add_summary(connection: AsyncConnection, identity: UUID) -> UUID:
    summary_id = uuid4()
    briefing = SummaryBriefing(
        summary_id=summary_id,
        playthrough_id=identity,
        observer_faction_id="house_carrow",
        requested_turn=0,
        trigger="major_event",
        facts=[
            SummaryFact(
                event_id=uuid4(),
                kind="uprising_started",
                turn=0,
                text_key="uprising_started",
                region_ids=["carrow"],
            )
        ],
    )
    await summary_delivery_repo.insert(
        connection, briefing, str(uuid4()), briefing_hash(briefing)
    )
    await connection.commit()
    return summary_id


OWNER = OWNER_USER_ID
