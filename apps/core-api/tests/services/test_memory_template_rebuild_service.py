"""Tests for app/services/memory_template_rebuild_service.py."""

import uuid
from datetime import UTC, datetime

import pytest
from app.db.models.user import User
from app.exceptions.memory_exceptions import MemoryTemplateBuildError
from app.integrations import memory_client
from app.models.memory_template import TemplateBuildOutcome, TemplateBuildResponse
from app.models.scenario import ScenarioCreate
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.user_repo import UserRepo
from app.services.memory_template_rebuild_service import rebuild_all_templates
from app.services.scenario_service import ScenarioService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def creator(db_session: AsyncSession) -> User:
    return await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator"
    )


async def _published_scenario(
    db_session: AsyncSession, user: User, revision: int, status: str = "published"
):
    scenario = await ScenarioService(ScenarioRepo(db_session)).create_scenario(
        user.user_id,
        ScenarioCreate(
            title="Rebuild Me",
            mode="newbie",
            complexity_tier="newbie",
            content_tag="all-ages",
        ),
    )
    stored = await ScenarioRepo(db_session).get_by_id(scenario.scenario_id)
    stored.status = status
    stored.publish_revision = revision
    stored.published_at = datetime.now(UTC)
    await db_session.flush()
    return stored


def _stub_build(monkeypatch, was_created: bool):
    calls = []

    async def _build(request):
        calls.append(request)
        return TemplateBuildOutcome(
            response=TemplateBuildResponse(
                template_id=request.scenario_id,
                direct_status="ready",
                enrichment_status="pending",
            ),
            was_created=was_created,
        )

    monkeypatch.setattr(memory_client, "build_template", _build)
    return calls


@pytest.mark.asyncio
async def test_dry_run_lists_scenarios_without_calling_memory(
    db_session: AsyncSession, creator: User, monkeypatch
):
    calls = _stub_build(monkeypatch, True)
    scenario = await _published_scenario(db_session, creator, 0)

    results = await rebuild_all_templates(db_session, is_dry_run=True)

    mine = [r for r in results if r.scenario_id == scenario.scenario_id]
    assert [(r.revision, r.status) for r in mine] == [(1, "would_build")]
    assert calls == []
    assert scenario.publish_revision == 0


@pytest.mark.asyncio
async def test_legacy_revision_zero_is_built_as_one_and_pinned(
    db_session: AsyncSession, creator: User, monkeypatch
):
    calls = _stub_build(monkeypatch, True)
    scenario = await _published_scenario(db_session, creator, 0)

    results = await rebuild_all_templates(db_session, is_dry_run=False)

    mine = [r for r in results if r.scenario_id == scenario.scenario_id]
    assert [(r.revision, r.status) for r in mine] == [(1, "built")]
    assert [
        c.publish_revision for c in calls if c.scenario_id == scenario.scenario_id
    ] == [1]
    assert scenario.publish_revision == 1


@pytest.mark.asyncio
async def test_second_run_reports_unchanged_and_keeps_revision(
    db_session: AsyncSession, creator: User, monkeypatch
):
    _stub_build(monkeypatch, False)
    scenario = await _published_scenario(db_session, creator, 2)

    results = await rebuild_all_templates(db_session, is_dry_run=False)

    mine = [r for r in results if r.scenario_id == scenario.scenario_id]
    assert [(r.revision, r.status) for r in mine] == [(2, "unchanged")]
    assert scenario.publish_revision == 2


@pytest.mark.asyncio
async def test_content_drift_is_skipped_not_failed(
    db_session: AsyncSession, creator: User, monkeypatch
):
    async def _conflict(request):
        raise MemoryTemplateBuildError("template_content_conflict", 409)

    monkeypatch.setattr(memory_client, "build_template", _conflict)
    scenario = await _published_scenario(db_session, creator, 2)

    results = await rebuild_all_templates(db_session, is_dry_run=False)

    mine = [r for r in results if r.scenario_id == scenario.scenario_id]
    assert [r.status for r in mine] == ["skipped_drift"]


@pytest.mark.asyncio
async def test_memory_outage_is_failed_and_does_not_pin_revision(
    db_session: AsyncSession, creator: User, monkeypatch
):
    async def _down(request):
        raise MemoryTemplateBuildError("unavailable")

    monkeypatch.setattr(memory_client, "build_template", _down)
    scenario = await _published_scenario(db_session, creator, 0)

    results = await rebuild_all_templates(db_session, is_dry_run=False)

    mine = [r for r in results if r.scenario_id == scenario.scenario_id]
    assert [r.status for r in mine] == ["failed"]
    assert scenario.publish_revision == 0


@pytest.mark.asyncio
async def test_drafts_and_never_published_scenarios_are_not_listed(
    db_session: AsyncSession, creator: User, monkeypatch
):
    _stub_build(monkeypatch, True)
    draft = await ScenarioService(ScenarioRepo(db_session)).create_scenario(
        creator.user_id,
        ScenarioCreate(
            title="Draft", mode="newbie", complexity_tier="newbie", content_tag=None
        ),
    )

    results = await rebuild_all_templates(db_session, is_dry_run=True)

    assert draft.scenario_id not in {r.scenario_id for r in results}
