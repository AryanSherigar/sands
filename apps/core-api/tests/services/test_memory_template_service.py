"""Tests for app/services/memory_template_service.py."""

import hashlib
import json
import uuid

import pytest
from app.db.models.user import User
from app.exceptions.memory_exceptions import MemoryTemplateBuildError
from app.integrations import memory_client
from app.models.entity import EntityCreate
from app.models.fact import FactCreate
from app.models.memory_template import (
    NewbieTemplateContent,
    TemplateBuildOutcome,
    TemplateBuildResponse,
)
from app.models.scenario import ScenarioCreate, ScenarioUpdate
from app.repositories.entity_repo import EntityRepo
from app.repositories.fact_repo import FactRepo
from app.repositories.map_repo import MapRepo
from app.repositories.scenario_entity_type_repo import ScenarioEntityTypeRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.user_repo import UserRepo
from app.services.entity_service import EntityService
from app.services.fact_service import FactService
from app.services.memory_template_service import (
    build_template_request,
    compute_content_hash,
    push_template,
)
from app.services.scenario_service import ScenarioService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def creator(db_session: AsyncSession) -> User:
    return await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator"
    )


async def _create_scenario(db_session: AsyncSession, user: User, mode: str):
    return await ScenarioService(ScenarioRepo(db_session)).create_scenario(
        user.user_id,
        ScenarioCreate(
            title="Template Scenario",
            mode=mode,
            complexity_tier=mode,
            content_tag="all-ages",
        ),
    )


async def _add_master_content(db_session: AsyncSession, user: User, scenario_id):
    entities = EntityService(
        EntityRepo(db_session),
        ScenarioRepo(db_session),
        FactRepo(db_session),
        ScenarioEntityTypeRepo(db_session),
    )
    warden = await entities.create_entity(
        scenario_id,
        user.user_id,
        EntityCreate(entity_type="character", canonical_name="The Warden"),
    )
    sigil = await entities.create_entity(
        scenario_id,
        user.user_id,
        EntityCreate(entity_type="item", canonical_name="Ember Sigil"),
    )
    await FactService(
        FactRepo(db_session), EntityRepo(db_session), ScenarioRepo(db_session)
    ).create_fact(
        scenario_id,
        user.user_id,
        FactCreate(
            subject_entity_id=warden.entity_id,
            predicate="vulnerable_to",
            object_entity_id=sigil.entity_id,
            hidden=True,
            when_active={"field": "flags.alarm", "op": "==", "value": True},
        ),
    )
    return warden, sigil


def _repos(db_session: AsyncSession):
    return EntityRepo(db_session), FactRepo(db_session), MapRepo(db_session)


@pytest.mark.asyncio
async def test_master_request_carries_entities_facts_and_flags(
    db_session: AsyncSession, creator: User
):
    scenario = await _create_scenario(db_session, creator, "master")
    warden, sigil = await _add_master_content(db_session, creator, scenario.scenario_id)
    stored = await ScenarioRepo(db_session).get_by_id(scenario.scenario_id)

    request = await build_template_request(stored, 3, *_repos(db_session))

    assert request.mode == "master"
    assert request.publish_revision == 3
    assert request.newbie is None
    assert {e.entity_id for e in request.master.entities} == {
        warden.entity_id,
        sigil.entity_id,
    }
    fact = request.master.facts[0]
    assert fact.hidden is True
    assert fact.when_active == {"field": "flags.alarm", "op": "==", "value": True}


@pytest.mark.asyncio
async def test_content_hash_is_stable_across_rebuilds(
    db_session: AsyncSession, creator: User
):
    scenario = await _create_scenario(db_session, creator, "master")
    await _add_master_content(db_session, creator, scenario.scenario_id)
    stored = await ScenarioRepo(db_session).get_by_id(scenario.scenario_id)

    first = await build_template_request(stored, 1, *_repos(db_session))
    second = await build_template_request(stored, 1, *_repos(db_session))

    assert first.content_hash == second.content_hash
    assert first.model_dump_json() == second.model_dump_json()


@pytest.mark.asyncio
async def test_content_hash_changes_when_content_changes(
    db_session: AsyncSession, creator: User
):
    scenario = await _create_scenario(db_session, creator, "master")
    await _add_master_content(db_session, creator, scenario.scenario_id)
    stored = await ScenarioRepo(db_session).get_by_id(scenario.scenario_id)
    before = await build_template_request(stored, 1, *_repos(db_session))

    await EntityService(
        EntityRepo(db_session),
        ScenarioRepo(db_session),
        FactRepo(db_session),
        ScenarioEntityTypeRepo(db_session),
    ).create_entity(
        scenario.scenario_id,
        creator.user_id,
        EntityCreate(entity_type="item", canonical_name="Brass Key"),
    )
    after = await build_template_request(stored, 1, *_repos(db_session))

    assert before.content_hash != after.content_hash


def test_content_hash_ignores_key_order_but_not_content():
    left = NewbieTemplateContent(world_lore="a", main_conflict="b")
    right = NewbieTemplateContent(main_conflict="b", world_lore="a")
    changed = NewbieTemplateContent(world_lore="a", main_conflict="c")

    assert compute_content_hash(left) == compute_content_hash(right)
    assert compute_content_hash(left) != compute_content_hash(changed)


@pytest.mark.asyncio
async def test_newbie_request_maps_world_data_keys(
    db_session: AsyncSession, creator: User
):
    scenario = await _create_scenario(db_session, creator, "newbie")
    service = ScenarioService(ScenarioRepo(db_session))
    await service.update_scenario(
        scenario.scenario_id,
        creator.user_id,
        ScenarioUpdate(
            world_data={
                "worldLore": "The Ashford forge supplies the city watch.",
                "singleLorePrompt": "A smith's tale.",
                "mainConflict": "The watch is corrupt.",
                "openingPrompt": "You wake at the forge.",
                "storyCards": [
                    {
                        "id": "b",
                        "type": "Character",
                        "name": "Mara",
                        "content": "Smith",
                    },
                    {"id": "a", "type": "Location", "name": "Forge", "content": "Hot"},
                ],
            }
        ),
    )
    stored = await ScenarioRepo(db_session).get_by_id(scenario.scenario_id)

    request = await build_template_request(stored, 1, *_repos(db_session))

    assert request.mode == "newbie"
    assert request.master is None
    assert request.newbie.world_lore.startswith("The Ashford forge")
    assert request.newbie.main_conflict == "The watch is corrupt."
    assert request.newbie.opening_prompt == "You wake at the forge."
    assert [card.card_id for card in request.newbie.story_cards] == ["a", "b"]


@pytest.mark.asyncio
async def test_newbie_request_carries_entities_with_aliases_and_facts(
    db_session: AsyncSession, creator: User
):
    scenario = await _create_scenario(db_session, creator, "newbie")
    entities = EntityService(
        EntityRepo(db_session),
        ScenarioRepo(db_session),
        FactRepo(db_session),
        ScenarioEntityTypeRepo(db_session),
    )
    mara = await entities.create_entity(
        scenario.scenario_id,
        creator.user_id,
        EntityCreate(
            entity_type="character",
            canonical_name="Mara",
            aliases=["Mara", "the keeper"],
            description="The keeper.",
        ),
    )
    lighthouse = await entities.create_entity(
        scenario.scenario_id,
        creator.user_id,
        EntityCreate(entity_type="location", canonical_name="The Lighthouse"),
    )
    await FactService(
        FactRepo(db_session), EntityRepo(db_session), ScenarioRepo(db_session)
    ).create_fact(
        scenario.scenario_id,
        creator.user_id,
        FactCreate(
            subject_entity_id=mara.entity_id,
            predicate="lives in",
            object_entity_id=lighthouse.entity_id,
            hidden=True,
        ),
    )
    stored = await ScenarioRepo(db_session).get_by_id(scenario.scenario_id)

    request = await build_template_request(stored, 1, *_repos(db_session))

    assert request.master is None
    by_id = {e.entity_id: e for e in request.newbie.entities}
    assert by_id[mara.entity_id].aliases == ["Mara", "the keeper"]
    assert by_id[mara.entity_id].description == "The keeper."
    assert set(by_id) == {mara.entity_id, lighthouse.entity_id}
    assert [(f.predicate, f.hidden) for f in request.newbie.facts] == [
        ("lives in", True)
    ]


def test_newbie_hash_without_cards_matches_the_pre_cards_shape():
    legacy = NewbieTemplateContent(world_lore="Salt")
    canonical = json.dumps(
        {
            "story_cards": [],
            "world_lore": "Salt",
            "single_lore_prompt": "",
            "main_conflict": "",
            "opening_prompt": "",
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    assert (
        compute_content_hash(legacy)
        == hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    )


@pytest.mark.asyncio
async def test_newbie_request_tolerates_missing_and_malformed_keys(
    db_session: AsyncSession, creator: User
):
    scenario = await _create_scenario(db_session, creator, "newbie")
    await ScenarioService(ScenarioRepo(db_session)).update_scenario(
        scenario.scenario_id,
        creator.user_id,
        ScenarioUpdate(
            world_data={
                "worldLore": 42,
                "storyCards": [
                    "not a card",
                    {"id": "", "name": "No id"},
                    {"id": "x", "name": ""},
                    {"id": "ok", "name": "Kept", "type": "Item", "content": "c"},
                ],
            }
        ),
    )
    stored = await ScenarioRepo(db_session).get_by_id(scenario.scenario_id)

    request = await build_template_request(stored, 1, *_repos(db_session))

    assert request.newbie.world_lore == ""
    assert [card.card_id for card in request.newbie.story_cards] == ["ok"]


@pytest.mark.asyncio
async def test_push_template_rejects_a_template_that_is_not_ready(
    db_session: AsyncSession, creator: User, monkeypatch
):
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
    scenario = await _create_scenario(db_session, creator, "newbie")
    stored = await ScenarioRepo(db_session).get_by_id(scenario.scenario_id)

    with pytest.raises(MemoryTemplateBuildError) as excinfo:
        await push_template(stored, 1, *_repos(db_session))

    assert excinfo.value.code == "template_not_ready"


@pytest.mark.asyncio
async def test_content_hash_does_not_depend_on_database_row_order(
    db_session: AsyncSession, creator: User, monkeypatch
):
    scenario = await _create_scenario(db_session, creator, "master")
    _warden, sigil = await _add_master_content(
        db_session, creator, scenario.scenario_id
    )
    await FactService(
        FactRepo(db_session), EntityRepo(db_session), ScenarioRepo(db_session)
    ).create_fact(
        scenario.scenario_id,
        creator.user_id,
        FactCreate(
            subject_entity_id=sigil.entity_id,
            predicate="glows",
            object_literal="faintly",
        ),
    )
    stored = await ScenarioRepo(db_session).get_by_id(scenario.scenario_id)
    in_order = await build_template_request(stored, 1, *_repos(db_session))

    real_entities = EntityRepo.list_by_scenario
    real_facts = FactRepo.list_by_scenario

    async def reversed_entities(self, scenario_id):
        return list(reversed(await real_entities(self, scenario_id)))

    async def reversed_facts(self, scenario_id):
        return list(reversed(await real_facts(self, scenario_id)))

    monkeypatch.setattr(EntityRepo, "list_by_scenario", reversed_entities)
    monkeypatch.setattr(FactRepo, "list_by_scenario", reversed_facts)
    shuffled = await build_template_request(stored, 1, *_repos(db_session))

    assert len(in_order.master.entities) == 2 and len(in_order.master.facts) == 2
    assert shuffled.content_hash == in_order.content_hash
    assert shuffled.model_dump_json() == in_order.model_dump_json()


async def _add_map_connection(db_session: AsyncSession, scenario_id, warden, sigil):
    from app.db.models.map_connection import MapConnection

    low, high = sorted([warden.entity_id, sigil.entity_id])
    db_session.add(
        MapConnection(
            scenario_id=scenario_id,
            entity_id_a=low,
            entity_id_b=high,
            label="Narrow stair",
        )
    )
    await db_session.flush()


@pytest.mark.asyncio
async def test_master_template_includes_it(db_session: AsyncSession, creator: User):
    scenario = await _create_scenario(db_session, creator, "master")
    warden, sigil = await _add_master_content(db_session, creator, scenario.scenario_id)
    await _add_map_connection(db_session, scenario.scenario_id, warden, sigil)
    stored = await ScenarioRepo(db_session).get_by_id(scenario.scenario_id)

    request = await build_template_request(stored, 1, *_repos(db_session))

    assert request.mode == "master"
    assert request.newbie is None
    assert [c.label for c in request.master.map_connections] == ["Narrow stair"]
    assert len(request.master.entities) == 2
    assert len(request.master.facts) == 1


@pytest.mark.asyncio
async def test_newbie_template_omits_master_data(
    db_session: AsyncSession, creator: User
):
    scenario = await _create_scenario(db_session, creator, "master")
    warden, sigil = await _add_master_content(db_session, creator, scenario.scenario_id)
    await _add_map_connection(db_session, scenario.scenario_id, warden, sigil)
    await ScenarioService(ScenarioRepo(db_session)).update_scenario(
        scenario.scenario_id, creator.user_id, ScenarioUpdate(mode="newbie")
    )
    stored = await ScenarioRepo(db_session).get_by_id(scenario.scenario_id)

    request = await build_template_request(stored, 1, *_repos(db_session))

    assert request.mode == "newbie"
    assert request.master is None
    assert not hasattr(request.newbie, "map_connections")
    assert {e.entity_id for e in request.newbie.entities} == {
        warden.entity_id,
        sigil.entity_id,
    }
    assert len(request.newbie.facts) == 1
