"""Guided creation: new scenario columns, entities.lore_document and legacy mapping."""

import asyncio
import importlib.util
import json
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.db.base import Base
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from tests.db.migration_test_helpers import (
    SCRATCH_URL,
)
from tests.db.migration_test_helpers import (
    migrated_scratch_database as migrated_scratch_database,
)

PREVIOUS_REVISION = "033_private_scenarios"
CURRENT_REVISION = "034_guided_creation"
INVITE_TABLE = "scenario_invites"
CREATOR_ID = "00000000-0000-0000-0000-0000000000a1"
LEGACY_ID = "00000000-0000-0000-0000-0000000000b1"
OPENED_ID = "00000000-0000-0000-0000-0000000000b2"
EMPTY_ID = "00000000-0000-0000-0000-0000000000b3"
MASTER_ID = "00000000-0000-0000-0000-0000000000b4"
NEW_SCENARIO_COLUMNS = {
    "mood_tags",
    "narrator_persona_document",
    "player_mode",
    "guide_seen_features",
}
INSERT_USER = (
    "INSERT INTO users (user_id, display_name, auth_provider_id) "
    f"VALUES ('{CREATOR_ID}', 'Creator', 'auth-guided-migration')"
)
LEGACY_WORLD_DATA = {
    "storyCards": [
        {"id": "c1", "type": "character", "name": "Mara", "content": "The keeper."},
        {"id": "c2", "type": "weird", "name": "The Door", "content": ""},
    ],
    "mainConflict": "A door appears in the sea.",
    "worldLore": "Salt and rust.",
    "openingPrompt": "You wake on the rocks.",
}


def _scenario_insert(
    scenario_id: str,
    mode: str,
    world_data: dict[str, object],
    opening_scene: str | None = None,
    narrator_persona: str | None = None,
) -> str:
    opening = "NULL" if opening_scene is None else f"'{opening_scene}'"
    persona = "NULL" if narrator_persona is None else f"'{narrator_persona}'"
    payload = json.dumps(world_data).replace("'", "''")
    return (
        "INSERT INTO scenarios (scenario_id, creator_id, title, complexity_tier, "
        "player_count_support, mode, world_data, opening_scene, narrator_persona) "
        f"VALUES ('{scenario_id}', '{CREATOR_ID}', 'S', 'newbie', 'solo', '{mode}', "
        f"CAST('{payload}' AS jsonb), {opening}, {persona})"
    )


def _only_guided_objects(obj, name, type_, reflected, compare_to):
    if type_ == "table":
        return name in {"scenarios", "entities", INVITE_TABLE}
    owner = getattr(getattr(obj, "table", None), "name", None)
    if owner == INVITE_TABLE:
        return True
    touched = NEW_SCENARIO_COLUMNS | {"lore_document", "player_mode"}
    return owner in {"scenarios", "entities"} and any(
        item in str(name) for item in touched
    )


async def _execute(*statements: str) -> None:
    engine = create_async_engine(SCRATCH_URL, poolclass=NullPool)
    async with engine.begin() as connection:
        for statement in statements:
            await connection.execute(text(statement))
    await engine.dispose()


async def _rows(statement: str) -> list[tuple]:
    engine = create_async_engine(SCRATCH_URL, poolclass=NullPool)
    async with engine.connect() as connection:
        rows = [tuple(row) for row in (await connection.execute(text(statement)))]
    await engine.dispose()
    return rows


async def _world_data(scenario_id: str) -> dict[str, object]:
    rows = await _rows(
        f"SELECT world_data::text FROM scenarios WHERE scenario_id = '{scenario_id}'"
    )
    return json.loads(rows[0][0])


async def _schema():
    engine = create_async_engine(SCRATCH_URL, poolclass=NullPool)
    async with engine.connect() as connection:

        def read(sync_connection):
            inspector = inspect(sync_connection)
            scenario_columns = {c["name"] for c in inspector.get_columns("scenarios")}
            entity_columns = {c["name"] for c in inspector.get_columns("entities")}
            tables = set(inspector.get_table_names())
            context = MigrationContext.configure(
                sync_connection,
                opts={"compare_type": True, "include_object": _only_guided_objects},
            )
            return (
                scenario_columns,
                entity_columns,
                tables,
                compare_metadata(context, Base.metadata),
            )

        result = await connection.run_sync(read)
    await engine.dispose()
    return result


async def _migrate_legacy_rows(config) -> None:
    await asyncio.to_thread(command.downgrade, config, PREVIOUS_REVISION)
    await _execute(
        INSERT_USER,
        _scenario_insert(
            LEGACY_ID, "newbie", LEGACY_WORLD_DATA, narrator_persona="Dry and slow"
        ),
        _scenario_insert(
            OPENED_ID,
            "newbie",
            {"openingPrompt": "Old opening"},
            opening_scene="Already written",
        ),
        _scenario_insert(EMPTY_ID, "newbie", {}),
        _scenario_insert(MASTER_ID, "master", {"mainConflict": "Keep the vigil."}),
    )
    await asyncio.to_thread(command.upgrade, config, CURRENT_REVISION)


async def test_schema_has_new_columns_and_matches_the_orm(migrated_scratch_database):
    scenario_columns, entity_columns, tables, differences = await _schema()
    assert scenario_columns >= NEW_SCENARIO_COLUMNS
    assert INVITE_TABLE in tables
    assert scenario_columns >= NEW_SCENARIO_COLUMNS
    assert "lore_document" in entity_columns
    assert differences == []


async def test_new_columns_have_safe_defaults(migrated_scratch_database):
    await _execute(INSERT_USER, _scenario_insert(EMPTY_ID, "newbie", {}))

    rows = await _rows(
        "SELECT mood_tags, player_mode, guide_seen_features::text, "
        f"narrator_persona_document FROM scenarios WHERE scenario_id = '{EMPTY_ID}'"
    )

    assert rows == [([], "written", "[]", None)]


async def test_an_unknown_player_mode_is_rejected(migrated_scratch_database):
    await _execute(INSERT_USER, _scenario_insert(EMPTY_ID, "newbie", {}))
    with pytest.raises(DBAPIError):
        await _execute(
            f"UPDATE scenarios SET player_mode = 'robot' WHERE scenario_id = '{EMPTY_ID}'"
        )


async def test_upgrade_maps_story_cards_to_entities(migrated_scratch_database):
    await _migrate_legacy_rows(migrated_scratch_database)

    rows = await _rows(
        "SELECT entity_type, canonical_name, description, aliases, "
        "lore_document::text FROM entities "
        f"WHERE scenario_id = '{LEGACY_ID}' ORDER BY canonical_name"
    )

    mara, door = rows
    assert mara[:4] == ("character", "Mara", "The keeper.", ["Mara"])
    assert json.loads(mara[4]) == {
        "blocks": [
            {"kind": "text", "question_id": None, "label": None, "text": "The keeper."}
        ]
    }
    assert door[:2] == ("other", "The Door")
    assert json.loads(door[4]) == {"blocks": []}
    assert "storyCards" not in await _world_data(LEGACY_ID)


async def test_upgrade_maps_story_text_to_documents(migrated_scratch_database):
    await _migrate_legacy_rows(migrated_scratch_database)

    world_data = await _world_data(LEGACY_ID)

    assert world_data["premiseDocument"] == {
        "blocks": [
            {
                "kind": "answer",
                "question_id": "stakes",
                "label": "What stands in their way?",
                "text": "A door appears in the sea.",
            }
        ]
    }
    assert world_data["premise"] == (
        "What stands in their way?: A door appears in the sea."
    )
    assert world_data["worldLoreDocument"] == {
        "blocks": [
            {
                "kind": "text",
                "question_id": None,
                "label": None,
                "text": "Salt and rust.",
            }
        ]
    }
    assert world_data["mainConflict"] == "A door appears in the sea."
    assert world_data["worldLore"] == "Salt and rust."
    persona = await _rows(
        "SELECT narrator_persona_document::text FROM scenarios "
        f"WHERE scenario_id = '{LEGACY_ID}'"
    )
    assert json.loads(persona[0][0])["blocks"][0]["text"] == "Dry and slow"


async def test_upgrade_copies_the_opening_only_when_empty(migrated_scratch_database):
    await _migrate_legacy_rows(migrated_scratch_database)

    rows = await _rows(
        "SELECT scenario_id::text, opening_scene FROM scenarios ORDER BY scenario_id"
    )

    assert dict(rows) == {
        LEGACY_ID: "You wake on the rocks.",
        OPENED_ID: "Already written",
        EMPTY_ID: None,
        MASTER_ID: None,
    }


async def test_upgrade_leaves_scenarios_without_legacy_text_untouched(
    migrated_scratch_database,
):
    await _migrate_legacy_rows(migrated_scratch_database)

    assert await _world_data(EMPTY_ID) == {}
    assert (
        await _rows(f"SELECT count(*) FROM entities WHERE scenario_id = '{EMPTY_ID}'")
    )[0] == (0,)


async def _rerun_data_migration() -> None:
    path = Path("app/db/migrations/versions/034_guided_creation.py")
    spec = importlib.util.spec_from_file_location("guided_creation_034", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_async_engine(SCRATCH_URL, poolclass=NullPool)
    async with engine.begin() as connection:
        await connection.run_sync(module.migrate_story_content)
    await engine.dispose()


async def test_upgrading_again_changes_nothing(migrated_scratch_database):
    await _migrate_legacy_rows(migrated_scratch_database)
    scenarios_before = await _rows(
        "SELECT scenario_id::text, world_data::text, opening_scene, "
        "narrator_persona_document::text FROM scenarios ORDER BY scenario_id"
    )
    entities_before = await _rows("SELECT count(*) FROM entities")

    await _rerun_data_migration()

    assert scenarios_before == await _rows(
        "SELECT scenario_id::text, world_data::text, opening_scene, "
        "narrator_persona_document::text FROM scenarios ORDER BY scenario_id"
    )
    assert entities_before == await _rows("SELECT count(*) FROM entities")


async def test_downgrade_restores_story_cards_from_entities(
    migrated_scratch_database,
):
    await _migrate_legacy_rows(migrated_scratch_database)

    await asyncio.to_thread(
        command.downgrade, migrated_scratch_database, PREVIOUS_REVISION
    )

    cards = (await _world_data(LEGACY_ID))["storyCards"]
    assert sorted((card["name"], card["type"], card["content"]) for card in cards) == [
        ("Mara", "character", "The keeper."),
        ("The Door", "other", ""),
    ]
    assert (await _rows("SELECT count(*) FROM entities")) == [(0,)]
    scenario_columns, entity_columns, tables, _ = await _schema()
    assert NEW_SCENARIO_COLUMNS.isdisjoint(scenario_columns)
    assert INVITE_TABLE not in tables
    assert "lore_document" not in entity_columns


def _document(text: str) -> str:
    block = {"kind": "text", "question_id": None, "label": None, "text": text}
    return json.dumps({"blocks": [block]})


async def _author_in_new_studio() -> None:
    world_data = {
        "premiseDocument": json.loads(_document("New premise")),
        "worldLoreDocument": json.loads(_document("New lore")),
    }
    payload = json.dumps(world_data).replace("'", "''")
    await _execute(
        "UPDATE scenarios SET opening_scene = 'New opening', "
        f"world_data = CAST('{payload}' AS jsonb), "
        f"narrator_persona_document = CAST('{_document('New voice')}' AS jsonb) "
        f"WHERE scenario_id = '{EMPTY_ID}'"
    )


async def test_downgrade_restores_legacy_fields_from_the_documents(
    migrated_scratch_database,
):
    await _migrate_legacy_rows(migrated_scratch_database)
    await _author_in_new_studio()

    await asyncio.to_thread(
        command.downgrade, migrated_scratch_database, PREVIOUS_REVISION
    )

    world_data = await _world_data(EMPTY_ID)
    assert world_data["mainConflict"] == "New premise"
    assert world_data["worldLore"] == "New lore"
    assert world_data["openingPrompt"] == "New opening"
    persona = await _rows(
        f"SELECT narrator_persona FROM scenarios WHERE scenario_id = '{EMPTY_ID}'"
    )
    assert persona == [("New voice",)]
    assert (await _world_data(LEGACY_ID))["openingPrompt"] == "You wake on the rocks."


async def _assert_downgrade_is_refused(config, reason: str) -> None:
    with pytest.raises(RuntimeError, match=reason):
        await asyncio.to_thread(command.downgrade, config, PREVIOUS_REVISION)
    assert (await _rows("SELECT count(*) FROM entities"))[0][0] > 0
    _, _, tables, _ = await _schema()
    assert INVITE_TABLE in tables


async def test_downgrade_refuses_when_a_newbie_story_has_facts(
    migrated_scratch_database,
):
    await _migrate_legacy_rows(migrated_scratch_database)
    await _execute(
        "INSERT INTO facts (scenario_id, subject_entity_id, predicate, object_literal) "
        f"SELECT '{LEGACY_ID}', entity_id, 'guards', 'the door' FROM entities "
        f"WHERE scenario_id = '{LEGACY_ID}' AND canonical_name = 'Mara'"
    )

    await _assert_downgrade_is_refused(migrated_scratch_database, "fact")
    assert (await _rows("SELECT count(*) FROM facts")) == [(1,)]


async def test_downgrade_refuses_when_a_newbie_story_has_a_player_card(
    migrated_scratch_database,
):
    await _migrate_legacy_rows(migrated_scratch_database)
    await _execute(
        "UPDATE entities SET is_player = true "
        f"WHERE scenario_id = '{LEGACY_ID}' AND canonical_name = 'Mara'"
    )

    await _assert_downgrade_is_refused(migrated_scratch_database, "player")


async def test_downgrade_refuses_when_a_document_is_newer_than_the_legacy_field(
    migrated_scratch_database,
):
    await _migrate_legacy_rows(migrated_scratch_database)
    world_data = await _world_data(LEGACY_ID)
    world_data["premiseDocument"] = json.loads(_document("Edited in the new Studio"))
    payload = json.dumps(world_data).replace("'", "''")
    await _execute(
        f"UPDATE scenarios SET world_data = CAST('{payload}' AS jsonb) "
        f"WHERE scenario_id = '{LEGACY_ID}'"
    )

    await _assert_downgrade_is_refused(migrated_scratch_database, "newer")


async def test_downgrade_never_touches_published_snapshots(
    migrated_scratch_database,
):
    await _migrate_legacy_rows(migrated_scratch_database)
    snapshot = json.dumps({"world_data": {"storyCards": [{"id": "c1"}]}})
    await _execute(
        "INSERT INTO playthroughs (scenario_id, created_by, scenario_version, "
        f"scenario_snapshot) VALUES ('{LEGACY_ID}', '{CREATOR_ID}', 1, "
        f"CAST('{snapshot}' AS jsonb))"
    )

    await asyncio.to_thread(
        command.downgrade, migrated_scratch_database, PREVIOUS_REVISION
    )

    rows = await _rows("SELECT scenario_snapshot::text FROM playthroughs")
    assert json.loads(rows[0][0]) == json.loads(snapshot)
