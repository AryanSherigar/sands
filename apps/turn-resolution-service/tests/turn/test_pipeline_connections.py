"""A blocked provider must leave a one-connection database pool usable."""

import asyncio
import uuid

import pytest
from app.models.auth import CurrentUser
from app.models.memory import MemoryContext
from app.models.turn import TurnRequestInput
from app.turn import pipeline
from app.turn.steps import (
    ai_orchestrator,
    context_retrieval,
    narration_audio_generator,
    scene_image_generator,
)
from app.turn.steps.state_writer import NarrationAudioResult
from pipeline_seed import seed_master_playthrough
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


async def _consume(response):
    return [event.event async for event in response.body_iterator]


@pytest.mark.parametrize("phase", ["retrieval", "narration", "image", "audio"])
async def test_external_wait_does_not_hold_connection(
    db_session, test_engine, monkeypatch, phase
):
    playthrough, participant = await seed_master_playthrough(
        db_session, {"mode": "master"}, {"current_location_id": "room"}
    )
    await db_session.commit()
    engine = create_async_engine(
        test_engine.url, pool_size=1, max_overflow=0, pool_timeout=0.2
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    paused, resume = asyncio.Event(), asyncio.Event()

    async def wait_at(name):
        if phase == name:
            paused.set()
            await resume.wait()

    async def retrieve(*args):
        await wait_at("retrieval")
        return MemoryContext()

    async def narrate(*args):
        yield "narration", "The door opens."
        await wait_at("narration")
        yield "narration_raw", "The door opens."

    async def image(*args):
        await wait_at("image")
        return "https://example.test/image.png", "a door"

    async def audio(*args, **kwargs):
        await wait_at("audio")
        return NarrationAudioResult("https://example.test/audio.wav")

    monkeypatch.setattr(context_retrieval, "retrieve_context", retrieve)
    monkeypatch.setattr(ai_orchestrator, "generate_narration", narrate)
    monkeypatch.setattr(scene_image_generator, "generate_scene_image", image)
    monkeypatch.setattr(narration_audio_generator, "generate_narration_audio", audio)
    response = await pipeline.run_turn(
        TurnRequestInput(
            playthrough_id=playthrough.playthrough_id,
            participant_id=participant.participant_id,
            client_action_id=uuid.uuid4(),
            action_text="Open the door.",
            action_mode="see",
            voice_output_requested=True,
        ),
        factory,
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    task = asyncio.create_task(_consume(response))
    try:
        await asyncio.wait_for(paused.wait(), 5)
        assert engine.pool.checkedout() == 0
        async with factory() as probe:
            assert await probe.scalar(select(1)) == 1
        resume.set()
        assert (await asyncio.wait_for(task, 5))[-1] == "done"
        assert engine.pool.checkedout() == 0
    finally:
        resume.set()
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await engine.dispose()


async def test_cancelled_narration_releases_pool_and_writes_no_turn(
    db_session, test_engine, monkeypatch
):
    from app.db.models.turn_log import TurnLog
    from sqlalchemy import func

    playthrough, participant = await seed_master_playthrough(
        db_session, {"mode": "master"}, {}
    )
    await db_session.commit()
    engine = create_async_engine(
        test_engine.url, pool_size=1, max_overflow=0, pool_timeout=0.2
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    paused = asyncio.Event()

    async def narrate(*args):
        yield "narration", "A beginning."
        paused.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(ai_orchestrator, "generate_narration", narrate)
    response = await pipeline.run_turn(
        TurnRequestInput(
            playthrough_id=playthrough.playthrough_id,
            participant_id=participant.participant_id,
            client_action_id=uuid.uuid4(),
            action_text="Wait.",
        ),
        factory,
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    task = asyncio.create_task(_consume(response))
    try:
        await asyncio.wait_for(paused.wait(), 5)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        assert engine.pool.checkedout() == 0
        async with factory() as session:
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(TurnLog)
                    .where(TurnLog.playthrough_id == playthrough.playthrough_id)
                )
                == 0
            )
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await engine.dispose()


async def test_overlapping_turns_commit_one_atomic_turn(
    db_session, test_engine, monkeypatch
):
    from app.db.models.memory_outbox import MemoryOutbox
    from app.db.models.playthrough import Playthrough
    from app.db.models.turn_log import TurnLog
    from sqlalchemy import func

    playthrough, participant = await seed_master_playthrough(
        db_session, {"mode": "master"}, {}
    )
    playthrough.memory_publish_revision = 0
    await db_session.commit()
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    paused, resume = asyncio.Event(), asyncio.Event()
    starts = 0

    async def narrate(*args):
        nonlocal starts
        starts += 1
        if starts == 2:
            paused.set()
        await resume.wait()
        yield "narration", "A turn."

    monkeypatch.setattr(ai_orchestrator, "generate_narration", narrate)
    responses = [
        await pipeline.run_turn(
            TurnRequestInput(
                playthrough_id=playthrough.playthrough_id,
                participant_id=participant.participant_id,
                client_action_id=uuid.uuid4(),
                action_text="Wait.",
            ),
            factory,
            CurrentUser(user_id=participant.user_id, token_version=1),
        )
        for _ in range(2)
    ]
    tasks = [asyncio.create_task(_consume(response)) for response in responses]
    try:
        await asyncio.wait_for(paused.wait(), 5)
        resume.set()
        events = await asyncio.wait_for(asyncio.gather(*tasks), 5)
        assert sorted(event_list[-1] for event_list in events) == ["degraded", "done"]
        async with factory() as session:
            for model in (TurnLog, MemoryOutbox):
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(model)
                        .where(model.playthrough_id == playthrough.playthrough_id)
                    )
                    == 1
                )
            stored = await session.get(Playthrough, playthrough.playthrough_id)
            assert stored.turn_count == 1
    finally:
        resume.set()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
