from uuid import uuid4

import httpx
import pytest
from app.config import Settings
from app.exceptions.access_exceptions import PlaythroughNotFoundError
from app.exceptions.command_exceptions import CampaignProgressError, CommandError
from app.integrations.llm_client import SpeechGradeAnswer
from app.models.api_battle_speech import SpeechTalkRequest
from app.models.speech_grading import MoodBriefing, SpeechBriefing
from app.models.world_battle import BattleSpeechStatus
from app.services.battle_speech_service import BattleSpeechService
from psycopg import AsyncConnection
from strategy_contracts.battle_speech import CrowdMood, CrowdReaction
from tests.engine.battles.test_battle_speech_state import take_command
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.helpers import mutation, seed_world

CHEER = CrowdReaction(mood=CrowdMood.CHEER, intensity=2)
BATTLE_ID = "battle_1"
SEEDED_VERSION = 1
SPEECH_WAVE = 1


class FakeSpeechClient:
    def __init__(
        self, mood_error: Exception | None = None, grade_error: Exception | None = None
    ) -> None:
        self._mood_error = mood_error
        self._grade_error = grade_error
        self.mood_briefings: list[MoodBriefing] = []
        self.grade_briefings: list[SpeechBriefing] = []

    async def react_to_talk(
        self, settings: Settings, briefing: MoodBriefing
    ) -> CrowdReaction:
        self.mood_briefings.append(briefing)
        if self._mood_error is not None:
            raise self._mood_error
        return CHEER

    async def grade_speech(
        self, settings: Settings, briefing: SpeechBriefing
    ) -> SpeechGradeAnswer:
        self.grade_briefings.append(briefing)
        if self._grade_error is not None:
            raise self._grade_error
        return SpeechGradeAnswer(
            addresses_fears=5, fits_ruler_character=5, promises_made=5
        )


def enabled() -> Settings:
    return Settings(speech_provider_enabled=True)


async def seeded_service(
    connection: AsyncConnection, client: FakeSpeechClient
) -> tuple[BattleSpeechService, object]:
    world, scenario = take_command(speech_ruleset=1)
    identity = await seed_world(connection, world, scenario)
    return BattleSpeechService(connection, enabled(), client), identity


def talk(name: str, version: int, index: int, text: str) -> SpeechTalkRequest:
    guard = mutation(name, version, turn=0, wave=SPEECH_WAVE)
    return SpeechTalkRequest(guard=guard, talk_index=index, text=text)


async def test_the_first_talk_gets_a_mood_reaction_and_changes_no_morale(
    db_connection: AsyncConnection,
) -> None:
    client = FakeSpeechClient()
    service, identity = await seeded_service(db_connection, client)
    before = await service.get_view(identity, OWNER_USER_ID, BATTLE_ID)
    result = await service.submit_talk(
        identity, OWNER_USER_ID, BATTLE_ID, talk("t1", SEEDED_VERSION, 1, "Hold!")
    )
    assert result.reaction == CHEER
    assert (result.is_complete, result.morale_delta_percent) == (False, None)
    assert client.mood_briefings[0].talks == ["Hold!"]
    assert client.grade_briefings == []
    assert before.next_talk == 1


async def test_a_mood_failure_falls_back_to_a_quiet_murmur(
    db_connection: AsyncConnection,
) -> None:
    client = FakeSpeechClient(mood_error=httpx.ConnectError("down"))
    service, identity = await seeded_service(db_connection, client)
    result = await service.submit_talk(
        identity, OWNER_USER_ID, BATTLE_ID, talk("t1", SEEDED_VERSION, 1, "Hold!")
    )
    assert result.reaction == CrowdReaction(mood=CrowdMood.MURMUR, intensity=1)


async def test_the_third_talk_grades_all_three_and_finishes_the_speech(
    db_connection: AsyncConnection,
) -> None:
    client = FakeSpeechClient()
    service, identity = await seeded_service(db_connection, client)
    version = SEEDED_VERSION
    for index, text in enumerate(["One", "Two", "Closing"], start=1):
        result = await service.submit_talk(
            identity, OWNER_USER_ID, BATTLE_ID, talk(f"t{index}", version, index, text)
        )
        version = result.state.world_version
    assert client.grade_briefings[0].talks == ["One", "Two", "Closing"]
    assert (result.is_complete, result.morale_delta_percent) == (True, 15)
    view = await service.get_view(identity, OWNER_USER_ID, BATTLE_ID)
    assert view.status == BattleSpeechStatus.DONE
    assert view.next_talk is None
    assert view.outcome is not None


async def test_a_grading_failure_still_finishes_with_a_zero_swing(
    db_connection: AsyncConnection,
) -> None:
    client = FakeSpeechClient(grade_error=TimeoutError())
    service, identity = await seeded_service(db_connection, client)
    version = SEEDED_VERSION
    for index, text in enumerate(["One", "Two", "Closing"], start=1):
        result = await service.submit_talk(
            identity, OWNER_USER_ID, BATTLE_ID, talk(f"t{index}", version, index, text)
        )
        version = result.state.world_version
    assert (result.is_complete, result.morale_delta_percent) == (True, 0)


async def test_retrying_the_same_operation_makes_no_second_model_call(
    db_connection: AsyncConnection,
) -> None:
    client = FakeSpeechClient()
    service, identity = await seeded_service(db_connection, client)
    request = talk("t1", SEEDED_VERSION, 1, "Hold!")
    first = await service.submit_talk(identity, OWNER_USER_ID, BATTLE_ID, request)
    second = await service.submit_talk(identity, OWNER_USER_ID, BATTLE_ID, request)
    assert second.reaction == first.reaction
    assert len(client.mood_briefings) == 1


async def test_an_out_of_order_or_repeated_talk_is_rejected(
    db_connection: AsyncConnection,
) -> None:
    client = FakeSpeechClient()
    service, identity = await seeded_service(db_connection, client)
    with pytest.raises(CampaignProgressError):
        await service.submit_talk(
            identity, OWNER_USER_ID, BATTLE_ID, talk("skip", SEEDED_VERSION, 2, "Two")
        )
    assert client.mood_briefings == []


async def test_skipping_finishes_the_speech_with_no_model_call(
    db_connection: AsyncConnection,
) -> None:
    client = FakeSpeechClient()
    service, identity = await seeded_service(db_connection, client)
    guard = mutation("skip", SEEDED_VERSION, turn=0, wave=SPEECH_WAVE)
    result = await service.skip(identity, OWNER_USER_ID, BATTLE_ID, guard)
    assert (result.is_complete, result.morale_delta_percent) == (True, 0)
    assert client.mood_briefings == [] and client.grade_briefings == []


async def test_a_stale_world_version_is_rejected(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await seeded_service(db_connection, FakeSpeechClient())
    with pytest.raises(CommandError):
        await service.submit_talk(
            identity, OWNER_USER_ID, BATTLE_ID, talk("stale", 99, 1, "Hold!")
        )


async def test_another_user_cannot_read_or_talk_into_the_speech(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await seeded_service(db_connection, FakeSpeechClient())
    stranger = uuid4()
    with pytest.raises(PlaythroughNotFoundError):
        await service.get_view(identity, stranger, BATTLE_ID)
    with pytest.raises(PlaythroughNotFoundError):
        await service.submit_talk(
            identity, stranger, BATTLE_ID, talk("sneaky", SEEDED_VERSION, 1, "Hi")
        )


async def test_the_view_of_a_battle_without_a_speech_is_not_found(
    db_connection: AsyncConnection,
) -> None:
    world, scenario = take_command(speech_ruleset=0)
    identity = await seed_world(db_connection, world, scenario)
    service = BattleSpeechService(db_connection, enabled(), FakeSpeechClient())
    with pytest.raises(CampaignProgressError):
        await service.get_view(identity, OWNER_USER_ID, BATTLE_ID)
