from uuid import UUID

from app.engine.battles.views import observed_battle, project_battle
from app.engine.world_document import world_from_document
from app.exceptions.access_exceptions import PlaythroughNotFoundError
from app.exceptions.command_exceptions import CommandError
from app.models.api_battle import BattlePage, ExchangeReportPage
from app.models.battle_progress import CampaignState
from app.models.world_battle import BattleView
from app.repositories import battle_exchange_repo, world_state_repo
from app.services.battle_projection import battle_page, exchange_report
from app.services.campaign_state import player_faction, project_state
from app.services.campaign_transaction import require_owner
from psycopg import AsyncConnection


class BattleService:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def load_state(self, playthrough_id: UUID, user_id: UUID) -> CampaignState:
        """Load an allowlisted state projection after checking ownership."""
        async with self._connection.transaction():
            playthrough = await require_owner(self._connection, playthrough_id, user_id)
            row = await world_state_repo.get_world_state(
                self._connection, playthrough_id
            )
            if row is None:
                raise PlaythroughNotFoundError()
            return project_state(
                world_from_document(row.document),
                playthrough.scenario,
                row.row_version,
                row.world_hash,
            )

    async def load_battle(
        self, playthrough_id: UUID, user_id: UUID, battle_id: str
    ) -> BattleView:
        """Unknown and unobserved battles produce the same observer-safe absence."""
        async with self._connection.transaction():
            playthrough = await require_owner(self._connection, playthrough_id, user_id)
            row = await world_state_repo.get_world_state(
                self._connection, playthrough_id
            )
            if row is None:
                raise PlaythroughNotFoundError()
            world = world_from_document(row.document)
            return project_battle(
                world, battle_id, player_faction(world), playthrough.scenario
            )

    async def list_battles(
        self, playthrough_id: UUID, user_id: UUID, after_id: str, limit: int
    ) -> BattlePage:
        """Page active-first observer battles with a version-scoped cursor."""
        state = await self.load_state(playthrough_id, user_id)
        return battle_page(state, after_id, limit)

    async def list_reports(
        self,
        playthrough_id: UUID,
        user_id: UUID,
        battle_id: str,
        after_exchange: int,
        limit: int,
    ) -> ExchangeReportPage:
        """Read immutable exchange evidence, projecting only the authenticated observer's losses."""
        async with self._connection.transaction():
            await require_owner(self._connection, playthrough_id, user_id)
            row = await world_state_repo.get_world_state(
                self._connection, playthrough_id
            )
            if row is None:
                raise PlaythroughNotFoundError()
            world = world_from_document(row.document)
            observer = player_faction(world)
            battle = observed_battle(world, battle_id, observer)
            if after_exchange > battle.total_exchanges:
                raise CommandError("invalid exchange cursor", "invalid_cursor", 422)
            receipts = await battle_exchange_repo.list_exchanges(
                self._connection, playthrough_id, battle_id, limit + 1, after_exchange
            )
            items = [
                exchange_report(receipt, battle, observer)
                for receipt in receipts[:limit]
            ]
            return ExchangeReportPage(
                items=items,
                next_after_exchange=(
                    items[-1].total_exchange if len(receipts) > limit else None
                ),
            )
