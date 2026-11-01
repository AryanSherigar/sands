from app.models.world_battle import ExchangeReceipt
from app.repositories import battle_exchange_repo

from tests.models.builders import PLAYTHROUGH_ID
from tests.repositories.helpers import seed_playthrough


def _receipt(
    battle_id: str, campaign_turn: int, total_exchange: int
) -> ExchangeReceipt:
    return ExchangeReceipt(
        battle_id=battle_id,
        campaign_turn=campaign_turn,
        exchange_index=1,
        total_exchange=total_exchange,
        input_hash="in",
        output_hash="out",
        rule_version="1",
    )


async def test_list_exchanges_for_turn_filters_by_campaign_turn(db_connection) -> None:
    await seed_playthrough(db_connection)
    receipts = [_receipt("b2", 4, 1), _receipt("b1", 3, 1), _receipt("b1", 4, 2)]
    await battle_exchange_repo.append_exchanges(db_connection, PLAYTHROUGH_ID, receipts)
    found = await battle_exchange_repo.list_exchanges_for_turn(
        db_connection, PLAYTHROUGH_ID, 4
    )
    assert [(item.battle_id, item.total_exchange) for item in found] == [
        ("b1", 2),
        ("b2", 1),
    ]
