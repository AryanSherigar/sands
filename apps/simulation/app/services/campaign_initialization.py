import secrets

from app.config import WORLD_SEED_UPPER_BOUND
from app.engine.hashing import world_hash
from app.engine.world_init import new_world
from app.exceptions.command_exceptions import CommandError
from app.models.battle_progress import InitializeCampaign, MutationResponse
from app.models.world_state import WorldState
from app.repositories import (
    operation_repo,
    playthrough_repo,
    world_snapshot_repo,
    world_state_repo,
)
from app.services.campaign_state import mutation_response, project_state, request_hash
from app.services.campaign_transaction import replay_operation
from psycopg import AsyncConnection
from strategy_contracts.publish_checks import check_publishable

INITIALIZATION_ACTOR = "service:initialize"
INITIALIZATION_ROUTE = "initialize"
SCENARIO_SCHEMA_VERSION = 1


def validate_initialization(request: InitializeCampaign) -> None:
    if not check_publishable(request.scenario).is_publishable:
        raise CommandError("scenario is not publishable", "invalid_scenario", 422)
    playable = {
        faction.id for faction in request.scenario.factions if faction.is_playable
    }
    if request.player_faction_id not in playable:
        raise CommandError("faction is not playable", "invalid_faction", 422)


async def initialize_campaign(
    connection: AsyncConnection, request: InitializeCampaign
) -> MutationResponse:
    """The internal route authenticates the service before calling this transaction."""
    digest = request_hash(INITIALIZATION_ROUTE, request.model_dump(mode="json"))
    async with connection.transaction():
        await operation_repo.lock_initialization(connection, request.playthrough_id)
        previous = await replay_operation(
            connection,
            request.playthrough_id,
            INITIALIZATION_ACTOR,
            request.operation_id,
            digest,
        )
        if previous is not None:
            return previous
        return await _initialize_locked(connection, request, digest)


async def _initialize_locked(
    connection: AsyncConnection, request: InitializeCampaign, digest: str
) -> MutationResponse:
    previous = await playthrough_repo.get_playthrough(
        connection, request.playthrough_id
    )
    if previous is not None:
        return await _existing_initialization(connection, request, digest)
    validate_initialization(request)
    world = initial_world(request)
    world_digest = world_hash(world)
    await playthrough_repo.insert_playthrough(
        connection,
        request.playthrough_id,
        request.owner_user_id,
        request.scenario,
        SCENARIO_SCHEMA_VERSION,
    )
    await persist_initial_world(connection, world, world_digest)
    state = project_state(world, request.scenario, 1, world_digest)
    response = mutation_response(state, request.operation_id)
    await record_initial_response(connection, request, digest, response)
    return response


async def _existing_initialization(
    connection: AsyncConnection, request: InitializeCampaign, digest: str
) -> MutationResponse:
    previous = await operation_repo.get_initialization(
        connection, request.playthrough_id, INITIALIZATION_ACTOR
    )
    if previous is None:
        raise CommandError("initialization identity conflicts", "idempotency_conflict")
    original_payload = request.model_dump(mode="json") | {
        "operation_id": previous.operation_id
    }
    if request_hash(INITIALIZATION_ROUTE, original_payload) != previous.request_hash:
        raise CommandError("initialization identity conflicts", "idempotency_conflict")
    response = previous.response.model_copy(
        update={"operation_id": request.operation_id}
    )
    await operation_repo.insert_operation(
        connection,
        request.playthrough_id,
        INITIALIZATION_ACTOR,
        digest,
        INITIALIZATION_ROUTE,
        response,
        previous.committed_sequence,
    )
    return response


def _seed_for(request: InitializeCampaign) -> int:
    if request.seed is not None:
        return request.seed
    return secrets.randbelow(WORLD_SEED_UPPER_BOUND)


def initial_world(request: InitializeCampaign) -> WorldState:
    return new_world(
        request.scenario,
        request.playthrough_id,
        _seed_for(request),
        request.player_faction_id,
        request.ruler,
    )


async def persist_initial_world(
    connection: AsyncConnection, world: WorldState, digest: str
) -> None:
    await world_state_repo.insert_world_state(
        connection,
        world.playthrough_id,
        world.schema_version,
        world.clock.turn,
        digest,
        world.model_dump(mode="json"),
    )
    await world_snapshot_repo.insert_snapshot(
        connection,
        world.playthrough_id,
        world.clock.turn,
        world.schema_version,
        digest,
        world.model_dump(mode="json"),
    )


async def record_initial_response(
    connection: AsyncConnection,
    request: InitializeCampaign,
    digest: str,
    response: MutationResponse,
) -> None:
    await operation_repo.insert_operation(
        connection,
        request.playthrough_id,
        INITIALIZATION_ACTOR,
        digest,
        INITIALIZATION_ROUTE,
        response,
        0,
    )
