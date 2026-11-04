"""Unit/integration tests for MapService."""

import uuid

import pytest
from app.db.models.user import User
from app.exceptions.map_exceptions import (
    MapConnectionDuplicateError,
    MapConnectionInvalidEntityError,
    MapModeError,
    MapNotFoundError,
    MapPinInvalidEntityError,
    MapPinNotFoundError,
    MapStartLocationConflictError,
)
from app.exceptions.scenario_exceptions import (
    ScenarioAccessDeniedError,
    ScenarioNotFoundError,
)
from app.models.entity import EntityCreate
from app.models.map import (
    MapConnectionCreate,
    MapCreate,
    MapPinCreate,
    MapPinUpdate,
    MapUpdate,
)
from app.models.scenario import ScenarioCreate
from app.repositories.entity_repo import EntityRepo
from app.repositories.fact_repo import FactRepo
from app.repositories.map_repo import MapRepo
from app.repositories.scenario_entity_type_repo import ScenarioEntityTypeRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.user_repo import UserRepo
from app.services.entity_service import EntityService
from app.services.map_service import MapService
from app.services.scenario_service import ScenarioService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def creator(db_session: AsyncSession) -> User:
    return await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator"
    )


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    return await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Other"
    )


@pytest.fixture
async def master_scenario(db_session: AsyncSession, creator: User):
    scenario_service = ScenarioService(ScenarioRepo(db_session))
    return await scenario_service.create_scenario(
        creator.user_id,
        ScenarioCreate(
            title="The Hollow Cairn", mode="master", complexity_tier="master"
        ),
    )


@pytest.fixture
async def newbie_scenario(db_session: AsyncSession, creator: User):
    scenario_service = ScenarioService(ScenarioRepo(db_session))
    return await scenario_service.create_scenario(
        creator.user_id,
        ScenarioCreate(
            title="A Freeform Tale", mode="newbie", complexity_tier="newbie"
        ),
    )


@pytest.fixture
def map_service(db_session: AsyncSession) -> MapService:
    return MapService(
        MapRepo(db_session), ScenarioRepo(db_session), EntityRepo(db_session)
    )


@pytest.fixture
def entity_service(db_session: AsyncSession) -> EntityService:
    return EntityService(
        EntityRepo(db_session),
        ScenarioRepo(db_session),
        FactRepo(db_session),
        ScenarioEntityTypeRepo(db_session),
    )


async def _create_location(
    entity_service: EntityService, scenario_id: uuid.UUID, user_id: uuid.UUID, name: str
):
    return await entity_service.create_entity(
        scenario_id,
        user_id,
        EntityCreate(entity_type="location", canonical_name=name),
    )


async def _create_character(
    entity_service: EntityService, scenario_id: uuid.UUID, user_id: uuid.UUID, name: str
):
    return await entity_service.create_entity(
        scenario_id,
        user_id,
        EntityCreate(entity_type="character", canonical_name=name),
    )


@pytest.mark.asyncio
async def test_create_map_rejects_newbie_mode_scenario(
    map_service: MapService, newbie_scenario, creator: User
):
    with pytest.raises(MapModeError):
        await map_service.create_map(
            newbie_scenario.scenario_id, creator.user_id, MapCreate(name="Overworld")
        )


@pytest.mark.asyncio
async def test_create_map_rejects_non_owner(
    map_service: MapService, master_scenario, other_user: User
):
    with pytest.raises(ScenarioAccessDeniedError):
        await map_service.create_map(
            master_scenario.scenario_id, other_user.user_id, MapCreate(name="Overworld")
        )


@pytest.mark.asyncio
async def test_create_map_rejects_missing_scenario(
    map_service: MapService, creator: User
):
    with pytest.raises(ScenarioNotFoundError):
        await map_service.create_map(
            uuid.uuid4(), creator.user_id, MapCreate(name="Overworld")
        )


@pytest.mark.asyncio
async def test_create_and_list_maps_ordered_by_display_order(
    map_service: MapService, master_scenario, creator: User
):
    await map_service.create_map(
        master_scenario.scenario_id,
        creator.user_id,
        MapCreate(name="Second", display_order=2),
    )
    await map_service.create_map(
        master_scenario.scenario_id,
        creator.user_id,
        MapCreate(name="First", display_order=1),
    )

    items = await map_service.list_maps(master_scenario.scenario_id, creator.user_id)
    assert [m.name for m in items] == ["First", "Second"]


@pytest.mark.asyncio
async def test_update_map(map_service: MapService, master_scenario, creator: User):
    created = await map_service.create_map(
        master_scenario.scenario_id, creator.user_id, MapCreate(name="Overworld")
    )
    updated = await map_service.update_map(
        master_scenario.scenario_id,
        created.map_id,
        creator.user_id,
        MapUpdate(name="Overworld Renamed", display_order=5),
    )
    assert updated.name == "Overworld Renamed"
    assert updated.display_order == 5


@pytest.mark.asyncio
async def test_update_map_not_found(
    map_service: MapService, master_scenario, creator: User
):
    with pytest.raises(MapNotFoundError):
        await map_service.update_map(
            master_scenario.scenario_id,
            uuid.uuid4(),
            creator.user_id,
            MapUpdate(name="Doesn't exist"),
        )


@pytest.mark.asyncio
async def test_update_map_scoped_to_owning_scenario(
    map_service: MapService, db_session: AsyncSession, master_scenario, creator: User
):
    other_scenario = await ScenarioService(ScenarioRepo(db_session)).create_scenario(
        creator.user_id,
        ScenarioCreate(title="Other", mode="master", complexity_tier="master"),
    )
    created = await map_service.create_map(
        master_scenario.scenario_id, creator.user_id, MapCreate(name="Overworld")
    )
    with pytest.raises(MapNotFoundError):
        await map_service.update_map(
            other_scenario.scenario_id,
            created.map_id,
            creator.user_id,
            MapUpdate(name="Hijacked"),
        )


@pytest.mark.asyncio
async def test_delete_map(map_service: MapService, master_scenario, creator: User):
    created = await map_service.create_map(
        master_scenario.scenario_id, creator.user_id, MapCreate(name="Overworld")
    )
    await map_service.delete_map(
        master_scenario.scenario_id, created.map_id, creator.user_id
    )

    items = await map_service.list_maps(master_scenario.scenario_id, creator.user_id)
    assert items == []


@pytest.mark.asyncio
async def test_create_pin_requires_location_entity(
    map_service: MapService,
    entity_service: EntityService,
    master_scenario,
    creator: User,
):
    scenario_map = await map_service.create_map(
        master_scenario.scenario_id, creator.user_id, MapCreate(name="Overworld")
    )
    character = await _create_character(
        entity_service, master_scenario.scenario_id, creator.user_id, "The Warden"
    )
    with pytest.raises(MapPinInvalidEntityError):
        await map_service.create_pin(
            master_scenario.scenario_id,
            scenario_map.map_id,
            creator.user_id,
            MapPinCreate(entity_id=character.entity_id, x=0.5, y=0.5),
        )


@pytest.mark.asyncio
async def test_create_and_list_pins(
    map_service: MapService,
    entity_service: EntityService,
    master_scenario,
    creator: User,
):
    scenario_map = await map_service.create_map(
        master_scenario.scenario_id, creator.user_id, MapCreate(name="Overworld")
    )
    location = await _create_location(
        entity_service, master_scenario.scenario_id, creator.user_id, "The Cairn"
    )
    created = await map_service.create_pin(
        master_scenario.scenario_id,
        scenario_map.map_id,
        creator.user_id,
        MapPinCreate(entity_id=location.entity_id, x=0.25, y=0.75),
    )
    assert created.x == 0.25
    assert created.y == 0.75

    items = await map_service.list_pins(
        master_scenario.scenario_id, scenario_map.map_id, creator.user_id
    )
    assert [p.pin_id for p in items] == [created.pin_id]


@pytest.mark.asyncio
async def test_create_pin_rejects_second_start_location(
    map_service: MapService,
    entity_service: EntityService,
    master_scenario,
    creator: User,
):
    scenario_map = await map_service.create_map(
        master_scenario.scenario_id, creator.user_id, MapCreate(name="Overworld")
    )
    location_a = await _create_location(
        entity_service, master_scenario.scenario_id, creator.user_id, "The Cairn"
    )
    location_b = await _create_location(
        entity_service, master_scenario.scenario_id, creator.user_id, "The Keep"
    )
    await map_service.create_pin(
        master_scenario.scenario_id,
        scenario_map.map_id,
        creator.user_id,
        MapPinCreate(
            entity_id=location_a.entity_id, x=0.1, y=0.1, is_start_location=True
        ),
    )
    with pytest.raises(MapStartLocationConflictError):
        await map_service.create_pin(
            master_scenario.scenario_id,
            scenario_map.map_id,
            creator.user_id,
            MapPinCreate(
                entity_id=location_b.entity_id, x=0.2, y=0.2, is_start_location=True
            ),
        )


@pytest.mark.asyncio
async def test_update_pin_to_start_location_rejects_when_another_exists(
    map_service: MapService,
    entity_service: EntityService,
    master_scenario,
    creator: User,
):
    scenario_map = await map_service.create_map(
        master_scenario.scenario_id, creator.user_id, MapCreate(name="Overworld")
    )
    location_a = await _create_location(
        entity_service, master_scenario.scenario_id, creator.user_id, "The Cairn"
    )
    location_b = await _create_location(
        entity_service, master_scenario.scenario_id, creator.user_id, "The Keep"
    )
    await map_service.create_pin(
        master_scenario.scenario_id,
        scenario_map.map_id,
        creator.user_id,
        MapPinCreate(
            entity_id=location_a.entity_id, x=0.1, y=0.1, is_start_location=True
        ),
    )
    pin_b = await map_service.create_pin(
        master_scenario.scenario_id,
        scenario_map.map_id,
        creator.user_id,
        MapPinCreate(entity_id=location_b.entity_id, x=0.2, y=0.2),
    )
    with pytest.raises(MapStartLocationConflictError):
        await map_service.update_pin(
            master_scenario.scenario_id,
            scenario_map.map_id,
            pin_b.pin_id,
            creator.user_id,
            MapPinUpdate(is_start_location=True),
        )


@pytest.mark.asyncio
async def test_update_pin_reaffirming_own_start_flag_does_not_conflict(
    map_service: MapService,
    entity_service: EntityService,
    master_scenario,
    creator: User,
):
    scenario_map = await map_service.create_map(
        master_scenario.scenario_id, creator.user_id, MapCreate(name="Overworld")
    )
    location = await _create_location(
        entity_service, master_scenario.scenario_id, creator.user_id, "The Cairn"
    )
    pin = await map_service.create_pin(
        master_scenario.scenario_id,
        scenario_map.map_id,
        creator.user_id,
        MapPinCreate(
            entity_id=location.entity_id, x=0.1, y=0.1, is_start_location=True
        ),
    )
    updated = await map_service.update_pin(
        master_scenario.scenario_id,
        scenario_map.map_id,
        pin.pin_id,
        creator.user_id,
        MapPinUpdate(x=0.9, is_start_location=True),
    )
    assert updated.x == 0.9
    assert updated.is_start_location is True


@pytest.mark.asyncio
async def test_delete_pin_not_found_for_other_map(
    map_service: MapService,
    entity_service: EntityService,
    master_scenario,
    creator: User,
):
    map_a = await map_service.create_map(
        master_scenario.scenario_id, creator.user_id, MapCreate(name="A")
    )
    map_b = await map_service.create_map(
        master_scenario.scenario_id, creator.user_id, MapCreate(name="B")
    )
    location = await _create_location(
        entity_service, master_scenario.scenario_id, creator.user_id, "The Cairn"
    )
    pin = await map_service.create_pin(
        master_scenario.scenario_id,
        map_a.map_id,
        creator.user_id,
        MapPinCreate(entity_id=location.entity_id, x=0.1, y=0.1),
    )
    with pytest.raises(MapPinNotFoundError):
        await map_service.delete_pin(
            master_scenario.scenario_id, map_b.map_id, pin.pin_id, creator.user_id
        )


@pytest.mark.asyncio
async def test_create_connection_rejects_self_link(
    map_service: MapService,
    entity_service: EntityService,
    master_scenario,
    creator: User,
):
    location = await _create_location(
        entity_service, master_scenario.scenario_id, creator.user_id, "The Cairn"
    )
    with pytest.raises(MapConnectionInvalidEntityError):
        await map_service.create_connection(
            master_scenario.scenario_id,
            creator.user_id,
            MapConnectionCreate(
                entity_id_a=location.entity_id, entity_id_b=location.entity_id
            ),
        )


@pytest.mark.asyncio
async def test_create_connection_rejects_non_location_entity(
    map_service: MapService,
    entity_service: EntityService,
    master_scenario,
    creator: User,
):
    location = await _create_location(
        entity_service, master_scenario.scenario_id, creator.user_id, "The Cairn"
    )
    character = await _create_character(
        entity_service, master_scenario.scenario_id, creator.user_id, "The Warden"
    )
    with pytest.raises(MapConnectionInvalidEntityError):
        await map_service.create_connection(
            master_scenario.scenario_id,
            creator.user_id,
            MapConnectionCreate(
                entity_id_a=location.entity_id, entity_id_b=character.entity_id
            ),
        )


@pytest.mark.asyncio
async def test_create_connection_normalizes_pair_order_and_rejects_duplicate(
    map_service: MapService,
    entity_service: EntityService,
    master_scenario,
    creator: User,
):
    location_a = await _create_location(
        entity_service, master_scenario.scenario_id, creator.user_id, "The Cairn"
    )
    location_b = await _create_location(
        entity_service, master_scenario.scenario_id, creator.user_id, "The Keep"
    )
    first_id, second_id = sorted([location_a.entity_id, location_b.entity_id])

    created = await map_service.create_connection(
        master_scenario.scenario_id,
        creator.user_id,
        MapConnectionCreate(
            entity_id_a=location_b.entity_id, entity_id_b=location_a.entity_id
        ),
    )
    assert created.entity_id_a == first_id
    assert created.entity_id_b == second_id

    with pytest.raises(MapConnectionDuplicateError):
        await map_service.create_connection(
            master_scenario.scenario_id,
            creator.user_id,
            MapConnectionCreate(
                entity_id_a=location_a.entity_id, entity_id_b=location_b.entity_id
            ),
        )


@pytest.mark.asyncio
async def test_list_and_delete_connection(
    map_service: MapService,
    entity_service: EntityService,
    master_scenario,
    creator: User,
):
    location_a = await _create_location(
        entity_service, master_scenario.scenario_id, creator.user_id, "The Cairn"
    )
    location_b = await _create_location(
        entity_service, master_scenario.scenario_id, creator.user_id, "The Keep"
    )
    created = await map_service.create_connection(
        master_scenario.scenario_id,
        creator.user_id,
        MapConnectionCreate(
            entity_id_a=location_a.entity_id, entity_id_b=location_b.entity_id
        ),
    )

    items = await map_service.list_connections(
        master_scenario.scenario_id, creator.user_id
    )
    assert [c.connection_id for c in items] == [created.connection_id]

    await map_service.delete_connection(
        master_scenario.scenario_id, created.connection_id, creator.user_id
    )
    items_after = await map_service.list_connections(
        master_scenario.scenario_id, creator.user_id
    )
    assert items_after == []
