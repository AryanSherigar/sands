from uuid import UUID

from app.repositories import epilogue_delivery_repo
from app.services.campaign_service import CampaignService
from psycopg import AsyncConnection
from strategy_contracts.epilogue import EpilogueBriefing

from tests.services.test_campaign_service import initialization


def _briefing(identity: UUID, ruler_name: str) -> EpilogueBriefing:
    return EpilogueBriefing(
        playthrough_id=identity,
        ruler_name=ruler_name,
        ending_id="default_defeat_capital_lost",
        ending_kind="defeat",
        ending_turn=2,
    )


async def test_the_first_briefing_for_a_playthrough_is_the_only_one_kept(
    db_connection: AsyncConnection,
) -> None:
    request = initialization()
    await CampaignService(db_connection).initialize(request)
    identity = request.playthrough_id
    await epilogue_delivery_repo.insert_if_absent(
        db_connection, _briefing(identity, "First"), "a" * 64
    )
    await epilogue_delivery_repo.insert_if_absent(
        db_connection, _briefing(identity, "Second"), "b" * 64
    )
    row = await epilogue_delivery_repo.get(db_connection, identity)
    assert row is not None
    assert row.briefing.ruler_name == "First"
    assert row.input_hash == "a" * 64
    assert row.status == "pending"
