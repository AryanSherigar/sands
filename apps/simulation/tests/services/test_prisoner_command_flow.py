from uuid import UUID

from app.engine.world_document import world_from_document
from app.models.battle_command import CommandStatus
from app.models.battle_progress import OperationGuard
from app.models.orders import HandlePrisonerOrder
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from app.repositories import world_state_repo
from app.services.campaign_service import CampaignService
from app.services.command_service import CommandService
from psycopg import AsyncConnection
from strategy_contracts.enums import TroopType
from strategy_contracts.overtures import OvertureKind
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.test_campaign_service import initialization

PLAYER = "house_carrow"
RIVAL = "house_dunwick"
PRISONER_ID = "prisoner_1"
RIVAL_STABILITY = 0
RIVAL_TREASURY = 100000


def ransomed_price_per_troop() -> int:
    return initialization().scenario.tuning.peace.ransom_gold_per_troop


async def _seed_with_captive(connection: AsyncConnection) -> tuple[UUID, int]:
    request = initialization()
    await CampaignService(connection).initialize(request)
    await connection.commit()
    row = await world_state_repo.get_world_state(connection, request.playthrough_id)
    assert row is not None
    world = world_from_document(row.document)
    world.prisoners.append(
        PrisonerState(
            id=PRISONER_ID,
            held_by_id=PLAYER,
            origin_faction_id=RIVAL,
            kind=PrisonerKind.TROOPS,
            troop_count=100,
            origin_battle_id="battle_1",
            troops_by_type={TroopType.INFANTRY: 100},
        )
    )
    world.factions[RIVAL].stability = RIVAL_STABILITY
    world.factions[RIVAL].treasury = RIVAL_TREASURY
    document = world.model_dump(mode="json")
    version = await world_state_repo.update_world_state(
        connection,
        request.playthrough_id,
        row.row_version,
        row.schema_version,
        row.turn,
        row.world_hash,
        document,
    )
    await connection.commit()
    assert version is not None
    return request.playthrough_id, version


def _guard(operation_id: str, version: int) -> OperationGuard:
    return OperationGuard(
        operation_id=operation_id,
        expected_world_version=version,
        expected_turn=0,
        expected_wave=0,
    )


async def _load_world(connection: AsyncConnection, playthrough_id: UUID):
    row = await world_state_repo.get_world_state(connection, playthrough_id)
    assert row is not None
    return world_from_document(row.document)


async def test_a_release_order_flows_through_the_service_and_the_turn(
    db_connection: AsyncConnection,
) -> None:
    playthrough_id, version = await _seed_with_captive(db_connection)
    before = await _load_world(db_connection, playthrough_id)
    reputation = before.factions[PLAYER].reputation
    order = HandlePrisonerOrder(
        faction_id=PLAYER, prisoner_id=PRISONER_ID, action="release"
    )

    await CommandService(db_connection).accept(
        playthrough_id, OWNER_USER_ID, _guard("release", version), order
    )
    await CampaignService(db_connection).begin(
        playthrough_id, OWNER_USER_ID, _guard("begin", version + 1)
    )

    after = await _load_world(db_connection, playthrough_id)
    assert all(item.id != PRISONER_ID for item in after.prisoners)
    assert after.factions[PLAYER].reputation > reputation
    applied = [c for c in after.accepted_commands if c.status == CommandStatus.APPLIED]
    assert any(isinstance(c.command, HandlePrisonerOrder) for c in applied)


async def _play_turn(connection: AsyncConnection, action: str | None):
    playthrough_id, version = await _seed_with_captive(connection)
    if action is not None:
        order = HandlePrisonerOrder(
            faction_id=PLAYER, prisoner_id=PRISONER_ID, action=action
        )
        await CommandService(connection).accept(
            playthrough_id, OWNER_USER_ID, _guard(action, version), order
        )
        version += 1
    await CampaignService(connection).begin(
        playthrough_id, OWNER_USER_ID, _guard("begin", version)
    )
    return await _load_world(connection, playthrough_id)


async def test_a_ransom_order_moves_exactly_the_price_through_the_turn(
    db_connection: AsyncConnection,
) -> None:
    control = await _play_turn(db_connection, None)
    ransomed = await _play_turn(db_connection, "ransom")

    price = 100 * ransomed_price_per_troop()
    assert all(item.id != PRISONER_ID for item in ransomed.prisoners)
    assert ransomed.peace.ransom_counters == []
    gained = ransomed.factions[PLAYER].treasury - control.factions[PLAYER].treasury
    paid = control.factions[RIVAL].treasury - ransomed.factions[RIVAL].treasury
    assert gained == price
    assert paid == price


async def test_a_calm_realm_answers_a_ransom_order_with_a_counter_not_a_payment(
    db_connection: AsyncConnection,
) -> None:
    playthrough_id, version = await _seed_with_captive(db_connection)
    row = await world_state_repo.get_world_state(db_connection, playthrough_id)
    world = world_from_document(row.document)
    world.factions[RIVAL].stability = 100
    await world_state_repo.update_world_state(
        db_connection,
        playthrough_id,
        row.row_version,
        row.schema_version,
        row.turn,
        row.world_hash,
        world.model_dump(mode="json"),
    )
    await db_connection.commit()
    order = HandlePrisonerOrder(
        faction_id=PLAYER, prisoner_id=PRISONER_ID, action="ransom"
    )

    await CommandService(db_connection).accept(
        playthrough_id, OWNER_USER_ID, _guard("ransom", version + 1), order
    )
    await CampaignService(db_connection).begin(
        playthrough_id, OWNER_USER_ID, _guard("begin", version + 2)
    )

    after = await _load_world(db_connection, playthrough_id)
    assert any(item.id == PRISONER_ID for item in after.prisoners)
    pending = after.progress.pending_negotiation
    assert pending is not None
    assert pending.overture.kind is OvertureKind.RANSOM_COUNTER
    assert after.progress.pending_scene_id is not None
    assert after.peace.ransom_counters == []
