from uuid import UUID, uuid4

from app.repositories import playthrough_repo
from psycopg import AsyncConnection
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.scene import (
    ScenePackage,
    SceneSituation,
    SceneType,
    TermsCardOutcome,
    TermsCardSpec,
    TermsResult,
)
from strategy_contracts.terms import TermKind

from tests.models.builders import PLAYTHROUGH_ID

OWNER_USER_ID = UUID("55555555-5555-5555-5555-555555555555")
SCENARIO_SCHEMA_VERSION = 1


async def seed_playthrough(
    connection: AsyncConnection, playthrough_id: UUID = PLAYTHROUGH_ID
) -> UUID:
    await playthrough_repo.insert_playthrough(
        connection,
        playthrough_id,
        OWNER_USER_ID,
        load_three_crowns(),
        SCENARIO_SCHEMA_VERSION,
    )
    return playthrough_id


def make_package(scene_id: UUID | None = None) -> ScenePackage:
    return ScenePackage(
        scene_id=scene_id or uuid4(),
        playthrough_id=PLAYTHROUGH_ID,
        scene_type=SceneType.NEGOTIATION,
        turn=3,
        situation=SceneSituation(summary="Ashford sues for peace."),
        allowed_outcomes=[TermsCardSpec(allowed_term_kinds=[TermKind.TRIBUTE])],
        exchange_cap=6,
        default_outcome=TermsCardOutcome(result=TermsResult.REFUSED),
    )
