from typing import Annotated

from app.config import get_settings
from app.db.pool import get_connection
from app.services.battle_service import BattleService
from app.services.battle_speech_service import BattleSpeechService
from app.services.campaign_service import CampaignService
from app.services.command_service import CommandService
from app.services.negotiation_service import NegotiationService
from app.services.proclamation_scene_service import ProclamationSceneService
from app.services.replay_service import ReplayService
from app.services.scene_exchange_service import SceneExchangeService
from app.services.turn_report_service import TurnReportService
from app.services.world_view_service import WorldViewService
from fastapi import Depends
from psycopg import AsyncConnection

Connection = Annotated[AsyncConnection, Depends(get_connection)]


def get_campaign_service(connection: Connection) -> CampaignService:
    return CampaignService(connection)


def get_battle_service(connection: Connection) -> BattleService:
    return BattleService(connection)


def get_command_service(connection: Connection) -> CommandService:
    return CommandService(connection)


def get_world_view_service(connection: Connection) -> WorldViewService:
    return WorldViewService(connection)


def get_replay_service(connection: Connection) -> ReplayService:
    return ReplayService(connection)


def get_turn_report_service(connection: Connection) -> TurnReportService:
    return TurnReportService(connection)


def get_negotiation_service(connection: Connection) -> NegotiationService:
    return NegotiationService(connection)


def get_scene_exchange_service(connection: Connection) -> SceneExchangeService:
    return SceneExchangeService(connection)


def get_battle_speech_service(connection: Connection) -> BattleSpeechService:
    return BattleSpeechService(connection, get_settings())


def get_proclamation_scene_service(
    connection: Connection,
) -> ProclamationSceneService:
    return ProclamationSceneService(connection)
