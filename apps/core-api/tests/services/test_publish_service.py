"""Unit/integration tests for PublishService."""

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from app.db.models.user import User
from app.exceptions.scenario_exceptions import (
    ScenarioAccessDeniedError,
    ScenarioAlreadyPublishingError,
    ScenarioNotFoundError,
    ScenarioValidationError,
)
from app.integrations import memory_client
from app.models.entity import EntityCreate
from app.models.fact import FactCreate
from app.models.scenario import ScenarioCreate
from app.repositories.entity_repo import EntityRepo
from app.repositories.fact_repo import FactRepo
from app.repositories.scenario_entity_type_repo import ScenarioEntityTypeRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.user_repo import UserRepo
from app.services.entity_service import EntityService
from app.services.fact_service import FactService
from app.services.publish_service import (
    PublishService,
    _check_content_tag,
    _check_content_tags,
    _check_strategy_document,
    _mark_publish_succeeded,
)
from app.services.scenario_service import ScenarioService
from sqlalchemy.ext.asyncio import AsyncSession
from strategy_contracts.examples import load_three_crowns


@pytest.fixture
async def sample_user(db_session: AsyncSession) -> User:
    user_repo = UserRepo(db_session)
    return await user_repo.create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator User"
    )


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    user_repo = UserRepo(db_session)
    return await user_repo.create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Other User"
    )


def _session_factory_for(session: AsyncSession):
    """Build a session-factory that reuses `session` instead of opening a new one.

    Keeps the background job on the same (uncommitted) test transaction so it
    can see rows the test set up earlier.
    """

    @asynccontextmanager
    async def _cm():
        yield session

    return lambda: _cm()


async def _create_draft(
    db_session: AsyncSession,
    user: User,
    content_tag: str | None = "all-ages",
    title: str = "Test Scenario",
    logline: str | None = "A lighthouse keeper finds a door in the sea.",
    opening_scene: str | None = "The tide is out.",
    world_data: dict[str, object] | None = None,
):
    service = ScenarioService(ScenarioRepo(db_session))
    return await service.create_scenario(
        user.user_id,
        ScenarioCreate(
            title=title,
            mode="newbie",
            complexity_tier="newbie",
            content_tag=content_tag,
            logline=logline,
            opening_scene=opening_scene,
            world_data=world_data or {},
        ),
    )


async def _publish_and_load(db_session: AsyncSession, user: User, created):
    repo = ScenarioRepo(db_session)
    await PublishService(repo).start_publish(created.scenario_id, user)
    await PublishService.run_publish_job(
        created.scenario_id, _session_factory_for(db_session)
    )
    return await repo.get_by_id(created.scenario_id)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "missing_label"),
    [
        ({"title": "   "}, "name"),
        ({"logline": None}, "one line idea"),
        ({"logline": "  "}, "one line idea"),
        ({"opening_scene": None}, "opening"),
        ({"opening_scene": "  "}, "opening"),
    ],
)
async def test_run_publish_job_newbie_requires_title_logline_and_opening(
    db_session: AsyncSession, sample_user: User, overrides, missing_label
):
    created = await _create_draft(db_session, sample_user, **overrides)

    failed = await _publish_and_load(db_session, sample_user, created)

    assert failed.status == "draft"
    assert failed.published_at is None
    assert missing_label in failed.publish_error


@pytest.mark.asyncio
async def test_run_publish_job_newbie_accepts_the_legacy_opening_prompt(
    db_session: AsyncSession, sample_user: User
):
    created = await _create_draft(
        db_session,
        sample_user,
        opening_scene=None,
        world_data={"openingPrompt": "You wake on the rocks."},
    )

    published = await _publish_and_load(db_session, sample_user, created)

    assert published.status == "published"


@pytest.mark.asyncio
async def test_start_publish_sets_status_publishing(
    db_session: AsyncSession, sample_user: User
):
    repo = ScenarioRepo(db_session)
    service = PublishService(repo)
    created = await _create_draft(db_session, sample_user)

    scenario = await service.start_publish(created.scenario_id, sample_user)

    assert scenario.status == "publishing"
    assert scenario.publish_error is None


@pytest.mark.asyncio
async def test_start_publish_rejects_non_creator(
    db_session: AsyncSession, sample_user: User, other_user: User
):
    repo = ScenarioRepo(db_session)
    service = PublishService(repo)
    created = await _create_draft(db_session, sample_user)

    with pytest.raises(ScenarioAccessDeniedError):
        await service.start_publish(created.scenario_id, other_user)


@pytest.mark.asyncio
async def test_start_publish_missing_scenario_404(
    db_session: AsyncSession, sample_user: User
):
    repo = ScenarioRepo(db_session)
    service = PublishService(repo)

    with pytest.raises(ScenarioNotFoundError):
        await service.start_publish(uuid.uuid4(), sample_user)


@pytest.mark.asyncio
async def test_start_publish_rejects_while_already_publishing(
    db_session: AsyncSession, sample_user: User
):
    repo = ScenarioRepo(db_session)
    service = PublishService(repo)
    created = await _create_draft(db_session, sample_user)
    await service.start_publish(created.scenario_id, sample_user)

    with pytest.raises(ScenarioAlreadyPublishingError):
        await service.start_publish(created.scenario_id, sample_user)


@pytest.mark.asyncio
async def test_run_publish_job_success_first_publish(
    db_session: AsyncSession, sample_user: User
):
    repo = ScenarioRepo(db_session)
    service = PublishService(repo)
    created = await _create_draft(db_session, sample_user, content_tag="all-ages")
    await service.start_publish(created.scenario_id, sample_user)

    await PublishService.run_publish_job(
        created.scenario_id, _session_factory_for(db_session)
    )

    published = await repo.get_by_id(created.scenario_id)
    assert published.status == "published"
    assert published.published_at is not None
    assert published.publish_error is None


@pytest.mark.asyncio
async def test_run_publish_job_success_bumps_publish_revision(
    db_session: AsyncSession, sample_user: User
):
    repo = ScenarioRepo(db_session)
    service = PublishService(repo)
    created = await _create_draft(db_session, sample_user, content_tag="all-ages")
    assert (await repo.get_by_id(created.scenario_id)).publish_revision == 0

    for expected_revision in (1, 2):
        await service.start_publish(created.scenario_id, sample_user)
        await PublishService.run_publish_job(
            created.scenario_id, _session_factory_for(db_session)
        )
        published = await repo.get_by_id(created.scenario_id)
        assert published.publish_revision == expected_revision


@pytest.mark.asyncio
async def test_run_publish_job_failure_keeps_publish_revision(
    db_session: AsyncSession, sample_user: User
):
    repo = ScenarioRepo(db_session)
    service = PublishService(repo)
    created = await _create_draft(db_session, sample_user, content_tag=None)
    await service.start_publish(created.scenario_id, sample_user)

    await PublishService.run_publish_job(
        created.scenario_id, _session_factory_for(db_session)
    )

    failed = await repo.get_by_id(created.scenario_id)
    assert failed.publish_revision == 0


@pytest.mark.asyncio
async def test_run_publish_job_snapshots_content_edited_at(
    db_session: AsyncSession, sample_user: User
):
    repo = ScenarioRepo(db_session)
    service = PublishService(repo)
    created = await _create_draft(db_session, sample_user, content_tag="all-ages")
    await service.start_publish(created.scenario_id, sample_user)
    before_job = await repo.get_by_id(created.scenario_id)
    edited_at_before_job = before_job.content_edited_at

    await PublishService.run_publish_job(
        created.scenario_id, _session_factory_for(db_session)
    )

    published = await repo.get_by_id(created.scenario_id)
    assert published.published_content_edited_at == edited_at_before_job
    assert published.content_edited_at == edited_at_before_job


@pytest.mark.asyncio
async def test_run_publish_job_master_mode_publishes_with_no_music_slots_set(
    db_session: AsyncSession, sample_user: User
):
    """Unset mood slots fall back to the built-in default track at playback
    time (MusicService.list_scenario_music), so publish must not require
    every slot to be explicitly filled first."""
    repo = ScenarioRepo(db_session)
    service = PublishService(repo)
    created = await _create_master_draft(db_session, sample_user)
    # Deliberately leave music slots unset.
    await service.start_publish(created.scenario_id, sample_user)

    await PublishService.run_publish_job(
        created.scenario_id, _session_factory_for(db_session)
    )

    published = await repo.get_by_id(created.scenario_id)
    assert published.status == "published"
    assert published.published_at is not None
    assert published.publish_error is None


@pytest.mark.asyncio
async def test_run_publish_job_newbie_mode_publishes_with_no_music_slots_set(
    db_session: AsyncSession, sample_user: User
):
    """Newbie mode has no UI to fill mood slots (MusicSlotEditor only renders
    in master mode's Studio layout), so it must publish fine with none set --
    regression test for the bug where every newbie scenario was unpublishable."""
    repo = ScenarioRepo(db_session)
    service = PublishService(repo)
    created = await _create_draft(db_session, sample_user, content_tag="all-ages")
    # Deliberately leave music slots unset.
    await service.start_publish(created.scenario_id, sample_user)

    await PublishService.run_publish_job(
        created.scenario_id, _session_factory_for(db_session)
    )

    published = await repo.get_by_id(created.scenario_id)
    assert published.status == "published"
    assert published.published_at is not None
    assert published.publish_error is None


@pytest.mark.asyncio
async def test_run_publish_job_first_failure_reverts_to_draft(
    db_session: AsyncSession, sample_user: User
):
    repo = ScenarioRepo(db_session)
    service = PublishService(repo)
    created = await _create_draft(db_session, sample_user, content_tag=None)
    await service.start_publish(created.scenario_id, sample_user)

    await PublishService.run_publish_job(
        created.scenario_id, _session_factory_for(db_session)
    )

    failed = await repo.get_by_id(created.scenario_id)
    assert failed.status == "draft"
    assert failed.published_at is None
    assert failed.publish_error is not None


@pytest.mark.asyncio
async def test_run_publish_job_republish_failure_keeps_scenario_live(
    db_session: AsyncSession, sample_user: User
):
    repo = ScenarioRepo(db_session)
    service = PublishService(repo)
    created = await _create_draft(db_session, sample_user, content_tag="all-ages")
    await service.start_publish(created.scenario_id, sample_user)
    await PublishService.run_publish_job(
        created.scenario_id, _session_factory_for(db_session)
    )

    # Creator clears the content tag, then re-publishes and it fails.
    scenario = await repo.get_by_id(created.scenario_id)
    scenario.content_tag = None
    await repo.update(scenario)
    await service.start_publish(created.scenario_id, sample_user)

    await PublishService.run_publish_job(
        created.scenario_id, _session_factory_for(db_session)
    )

    failed = await repo.get_by_id(created.scenario_id)
    assert failed.status == "publish_failed"
    assert failed.published_at is not None  # still considered live
    assert failed.publish_error is not None


async def _create_master_draft(db_session: AsyncSession, user: User):
    service = ScenarioService(ScenarioRepo(db_session))
    return await service.create_scenario(
        user.user_id,
        ScenarioCreate(
            title="The Hollow Cairn",
            mode="master",
            complexity_tier="master",
            content_tag="all-ages",
        ),
    )


def _capture_template_calls(monkeypatch):
    """Patch memory_client.build_template and return the list of requests it
    was called with, in order."""
    calls = []
    original = memory_client.build_template

    async def _spy(request):
        calls.append(request)
        return await original(request)

    monkeypatch.setattr(memory_client, "build_template", _spy)
    return calls


@pytest.mark.asyncio
async def test_run_publish_job_master_mode_sends_entities_and_facts(
    db_session: AsyncSession, sample_user: User, monkeypatch
):
    calls = _capture_template_calls(monkeypatch)
    service = PublishService(ScenarioRepo(db_session))
    created = await _create_master_draft(db_session, sample_user)

    entity_service = EntityService(
        EntityRepo(db_session),
        ScenarioRepo(db_session),
        FactRepo(db_session),
        ScenarioEntityTypeRepo(db_session),
    )
    warden = await entity_service.create_entity(
        created.scenario_id,
        sample_user.user_id,
        EntityCreate(entity_type="character", canonical_name="The Warden"),
    )
    sigil = await entity_service.create_entity(
        created.scenario_id,
        sample_user.user_id,
        EntityCreate(entity_type="item", canonical_name="Ember Sigil"),
    )
    fact_service = FactService(
        FactRepo(db_session), EntityRepo(db_session), ScenarioRepo(db_session)
    )
    await fact_service.create_fact(
        created.scenario_id,
        sample_user.user_id,
        FactCreate(
            subject_entity_id=warden.entity_id,
            predicate="vulnerable_to",
            object_entity_id=sigil.entity_id,
            hidden=True,
        ),
    )

    await service.start_publish(created.scenario_id, sample_user)
    await PublishService.run_publish_job(
        created.scenario_id, _session_factory_for(db_session)
    )

    assert len(calls) == 1
    request = calls[0]
    assert request.mode == "master"
    assert {e.entity_id for e in request.master.entities} == {
        warden.entity_id,
        sigil.entity_id,
    }
    assert len(request.master.facts) == 1
    fact = request.master.facts[0]
    assert fact.subject_entity_id == warden.entity_id
    assert fact.object_entity_id == sigil.entity_id
    assert fact.predicate == "vulnerable_to"
    assert fact.hidden is True  # hidden flag survives the ingest round-trip

    published = await ScenarioRepo(db_session).get_by_id(created.scenario_id)
    assert published.status == "published"


@pytest.mark.asyncio
async def test_run_publish_job_newbie_mode_sends_world_data_only(
    db_session: AsyncSession, sample_user: User, monkeypatch
):
    """Regression: newbie-mode publish is unchanged by the master-mode branch."""
    calls = _capture_template_calls(monkeypatch)
    service = PublishService(ScenarioRepo(db_session))
    created = await _create_draft(db_session, sample_user)
    await service.start_publish(created.scenario_id, sample_user)

    await PublishService.run_publish_job(
        created.scenario_id, _session_factory_for(db_session)
    )

    assert len(calls) == 1
    request = calls[0]
    assert request.mode == "newbie"
    assert request.master is None
    assert request.newbie is not None


@pytest.mark.asyncio
async def test_run_publish_job_empty_master_mode_scenario_still_ingests(
    db_session: AsyncSession, sample_user: User, monkeypatch
):
    """A master-mode scenario with no entities/facts yet is still valid to
    publish — ingestion runs with empty lists, not skipped."""
    calls = _capture_template_calls(monkeypatch)
    service = PublishService(ScenarioRepo(db_session))
    created = await _create_master_draft(db_session, sample_user)
    await service.start_publish(created.scenario_id, sample_user)

    await PublishService.run_publish_job(
        created.scenario_id, _session_factory_for(db_session)
    )

    assert len(calls) == 1
    assert calls[0].mode == "master"
    assert calls[0].master.entities == []
    assert calls[0].master.facts == []

    published = await ScenarioRepo(db_session).get_by_id(created.scenario_id)
    assert published.status == "published"


def test_check_content_tag_raises_for_missing_or_invalid_tag():
    class _Fake:
        content_tag = None

    with pytest.raises(ScenarioValidationError):
        _check_content_tag(_Fake())

    _Fake.content_tag = "not-a-real-tag"
    with pytest.raises(ScenarioValidationError):
        _check_content_tag(_Fake())

    _Fake.content_tag = "all-ages"
    _check_content_tag(_Fake())  # does not raise


def test_check_content_tags_allows_none_and_rejects_a_retired_tag():
    _check_content_tags(SimpleNamespace(content_tags=[]))  # does not raise
    _check_content_tags(SimpleNamespace(content_tags=["noir-atmosphere"]))

    with pytest.raises(ScenarioValidationError):
        _check_content_tags(
            SimpleNamespace(content_tags=["noir-atmosphere", "retired-tag"])
        )


@pytest.mark.asyncio
async def test_run_publish_job_awards_worldmaker_at_publish_time(
    db_session: AsyncSession, sample_user: User
):
    from app.repositories.achievement_repo import AchievementRepo

    repo = ScenarioRepo(db_session)
    service = PublishService(repo)
    created = await _create_draft(db_session, sample_user, content_tag="all-ages")
    await service.start_publish(created.scenario_id, sample_user)

    await PublishService.run_publish_job(
        created.scenario_id, _session_factory_for(db_session)
    )

    earned = {
        row.key: row.earned_at
        for row in await AchievementRepo(db_session).list_earned(sample_user.user_id)
    }
    assert "worldmaker" in earned
    published = await repo.get_by_id(created.scenario_id)
    assert abs((earned["worldmaker"] - published.published_at).total_seconds()) < 5


@pytest.mark.asyncio
async def test_failed_publish_does_not_award_worldmaker(
    db_session: AsyncSession, sample_user: User
):
    from app.repositories.achievement_repo import AchievementRepo

    repo = ScenarioRepo(db_session)
    service = PublishService(repo)
    created = await _create_draft(db_session, sample_user, content_tag=None)
    await service.start_publish(created.scenario_id, sample_user)

    await PublishService.run_publish_job(
        created.scenario_id, _session_factory_for(db_session)
    )

    failed = await repo.get_by_id(created.scenario_id)
    assert failed.status != "published"
    assert await AchievementRepo(db_session).list_earned(sample_user.user_id) == []


@pytest.fixture
def publish_quota(rate_limit_enabled):
    from app.services.rate_limit.quota_service import QuotaService

    return QuotaService(rate_limit_enabled)


@pytest.mark.asyncio
async def test_start_publish_consumes_publish_quota(
    db_session: AsyncSession, sample_user: User, publish_quota, monkeypatch
):
    from app.config import settings
    from app.exceptions.rate_limit_exceptions import RateLimitExceededError

    monkeypatch.setattr(settings, "quota_publish_per_user", 0)
    service = PublishService(ScenarioRepo(db_session), publish_quota)
    created = await _create_draft(db_session, sample_user)

    with pytest.raises(RateLimitExceededError):
        await service.start_publish(created.scenario_id, sample_user)

    scenario = await ScenarioRepo(db_session).get_by_id(created.scenario_id)
    assert scenario.status == "draft"


@pytest.mark.asyncio
async def test_publish_ingestion_failure_refunds_quota(
    db_session: AsyncSession, sample_user: User, publish_quota, monkeypatch
):
    from app.services.rate_limit.policies import QuotaFeature

    async def _failing_ingest(request):
        raise RuntimeError("memory layer down")

    monkeypatch.setattr(memory_client, "build_template", _failing_ingest)
    service = PublishService(ScenarioRepo(db_session), publish_quota)
    created = await _create_draft(db_session, sample_user)
    await service.start_publish(created.scenario_id, sample_user)

    await PublishService.run_publish_job(
        created.scenario_id, _session_factory_for(db_session), publish_quota
    )

    used = await publish_quota.used_today(QuotaFeature.PUBLISH, sample_user.user_id)
    assert used == 0


@pytest.mark.asyncio
async def test_publish_validation_failure_keeps_quota_spent(
    db_session: AsyncSession, sample_user: User, publish_quota
):
    from app.services.rate_limit.policies import QuotaFeature

    service = PublishService(ScenarioRepo(db_session), publish_quota)
    created = await _create_draft(db_session, sample_user, content_tag=None)
    await service.start_publish(created.scenario_id, sample_user)

    await PublishService.run_publish_job(
        created.scenario_id, _session_factory_for(db_session), publish_quota
    )

    used = await publish_quota.used_today(QuotaFeature.PUBLISH, sample_user.user_id)
    assert used == 1


@pytest.mark.asyncio
async def test_run_publish_job_requests_next_revision_then_pins_it(
    db_session: AsyncSession, sample_user: User, monkeypatch
):
    calls = _capture_template_calls(monkeypatch)
    repo = ScenarioRepo(db_session)
    service = PublishService(repo)
    created = await _create_draft(db_session, sample_user)

    for _ in range(2):
        await service.start_publish(created.scenario_id, sample_user)
        await PublishService.run_publish_job(
            created.scenario_id, _session_factory_for(db_session)
        )

    assert [call.publish_revision for call in calls] == [1, 2]
    assert (await repo.get_by_id(created.scenario_id)).publish_revision == 2


@pytest.mark.asyncio
async def test_run_publish_job_memory_rejection_keeps_revision_and_records_code(
    db_session: AsyncSession, sample_user: User, monkeypatch
):
    from app.exceptions.memory_exceptions import MemoryTemplateBuildError

    async def _reject(request):
        raise MemoryTemplateBuildError("template_content_conflict", 409)

    monkeypatch.setattr(memory_client, "build_template", _reject)
    repo = ScenarioRepo(db_session)
    service = PublishService(repo)
    created = await _create_draft(db_session, sample_user)
    await service.start_publish(created.scenario_id, sample_user)

    await PublishService.run_publish_job(
        created.scenario_id, _session_factory_for(db_session)
    )

    failed = await repo.get_by_id(created.scenario_id)
    assert failed.publish_revision == 0
    assert failed.status == "draft"
    assert "template_content_conflict" in failed.publish_error


@pytest.mark.asyncio
async def test_run_publish_job_template_not_ready_does_not_publish(
    db_session: AsyncSession, sample_user: User, monkeypatch
):
    from app.models.memory_template import TemplateBuildOutcome, TemplateBuildResponse

    async def _building(request):
        return TemplateBuildOutcome(
            response=TemplateBuildResponse(
                template_id=request.scenario_id,
                direct_status="building",
                enrichment_status="not_needed",
            ),
            was_created=True,
        )

    monkeypatch.setattr(memory_client, "build_template", _building)
    repo = ScenarioRepo(db_session)
    service = PublishService(repo)
    created = await _create_draft(db_session, sample_user)
    await service.start_publish(created.scenario_id, sample_user)

    await PublishService.run_publish_job(
        created.scenario_id, _session_factory_for(db_session)
    )

    failed = await repo.get_by_id(created.scenario_id)
    assert failed.publish_revision == 0
    assert failed.status != "published"


@pytest.mark.asyncio
async def test_strategy_publish_rejects_shared_blocking_checks(
    db_session: AsyncSession, sample_user: User
):
    scenario = await ScenarioService(ScenarioRepo(db_session)).create_scenario(
        sample_user.user_id,
        ScenarioCreate(
            title="Border Kingdoms",
            mode="strategy",
            complexity_tier="master",
            content_tag="all-ages",
            strategy_document={"schema_version": 1},
        ),
    )

    failed = await _publish_and_load(db_session, sample_user, scenario)

    assert failed.status == "draft"
    assert "Strategy scenario cannot publish" in (failed.publish_error or "")


def _three_crowns_with(mutate) -> dict[str, object]:
    document = load_three_crowns().model_dump(mode="json")
    mutate(document)
    return document


def _drop_armies(document: dict[str, object]) -> None:
    document["starting"]["armies"] = []


def _zero_wealth(document: dict[str, object]) -> None:
    for setup in document["starting"]["regions"]:
        setup["wealth"] = 0


@pytest.mark.parametrize(
    ("mutate", "expected_message"),
    [(_drop_armies, "has no army"), (_zero_wealth, "starts with no wealth")],
)
def test_strategy_publish_blocks_an_empty_starting_situation(mutate, expected_message):
    scenario = SimpleNamespace(
        mode="strategy", strategy_document=_three_crowns_with(mutate)
    )

    with pytest.raises(ScenarioValidationError, match=expected_message):
        _check_strategy_document(scenario)


def test_strategy_publish_accepts_the_three_crowns_start():
    scenario = SimpleNamespace(
        mode="strategy", strategy_document=load_three_crowns().model_dump(mode="json")
    )

    _check_strategy_document(scenario)


def test_strategy_publish_check_uses_shared_contract():
    scenario = SimpleNamespace(mode="strategy", strategy_document={"schema_version": 1})

    with pytest.raises(
        ScenarioValidationError, match="Strategy scenario cannot publish"
    ):
        _check_strategy_document(scenario)


def _scenario_to_publish(mode: str, document: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(
        mode=mode,
        strategy_document=document,
        published_strategy_document=None,
        status="publishing",
        publish_revision=0,
        published_at=None,
        published_content_edited_at=None,
        publish_error=None,
    )


def test_publishing_a_strategy_scenario_pins_a_copy_of_its_document() -> None:
    document = {"schema_version": 1, "tuning": {"orders_per_turn": 6}}
    scenario = _scenario_to_publish("strategy", document)

    _mark_publish_succeeded(scenario, datetime.now(UTC), 1)
    document["tuning"]["orders_per_turn"] = 9

    assert scenario.published_strategy_document == {
        "schema_version": 1,
        "tuning": {"orders_per_turn": 6},
    }


def test_publishing_other_modes_pins_nothing() -> None:
    scenario = _scenario_to_publish("master", {})

    _mark_publish_succeeded(scenario, datetime.now(UTC), 1)

    assert scenario.published_strategy_document is None
