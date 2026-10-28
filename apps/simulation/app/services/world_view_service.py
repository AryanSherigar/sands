from uuid import UUID

from app.engine.world_document import world_from_document
from app.exceptions.access_exceptions import PlaythroughNotFoundError
from app.models.api_battle import CampaignWorldView
from app.repositories import summary_delivery_repo, world_state_repo
from app.services.campaign_transaction import require_owner
from app.services.world_projection import project_world
from psycopg import AsyncConnection


class WorldViewService:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def load_world(
        self, playthrough_id: UUID, user_id: UUID
    ) -> CampaignWorldView:
        """Return only owner data and observed regions, never the canonical world document."""
        async with self._connection.transaction():
            playthrough = await require_owner(self._connection, playthrough_id, user_id)
            row = await world_state_repo.get_world_state(
                self._connection, playthrough_id
            )
            if row is None:
                raise PlaythroughNotFoundError()
            view = project_world(
                world_from_document(row.document),
                playthrough.scenario,
                row.row_version,
                row.world_hash,
            )

            view.summary_availability = await summary_delivery_repo.availability(
                self._connection, playthrough_id
            )
            return view
