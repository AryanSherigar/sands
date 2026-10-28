"""Guided creation: story documents, mood, player mode, cards and invite links.

Adds the scenario columns the Studio Guide writes, entities.lore_document and
the scenario_invites table, and maps legacy newbie content into the new shape:
storyCards become entities, mainConflict and worldLore become one-block lore
documents, openingPrompt fills an empty opening_scene and narrator_persona
becomes a one-block document. Published playthrough snapshots are never read
or written.

The downgrade refuses (like 033) when it would lose data it cannot represent:
facts or authored player cards in newbie stories, and documents edited after
the upgrade. Otherwise it writes the documents back into the legacy fields and
turns cards back into storyCards.

Revision ID: 034_guided_creation
Revises: 033_private_scenarios
"""

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "034_guided_creation"
down_revision: str | None = "033_private_scenarios"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None

PLAYER_MODE_CONSTRAINT = "ck_scenarios_player_mode"
INVITE_TABLE = "scenario_invites"
KEY_STORY_CARDS = "storyCards"
KEY_MAIN_CONFLICT = "mainConflict"
KEY_WORLD_LORE = "worldLore"
KEY_OPENING_PROMPT = "openingPrompt"
KEY_PREMISE = "premise"
KEY_PREMISE_DOCUMENT = "premiseDocument"
KEY_WORLD_LORE_DOCUMENT = "worldLoreDocument"
STAKES_QUESTION_ID = "stakes"
STAKES_LABEL = "What stands in their way?"
DOCUMENT_LEGACY_FIELDS = (
    (KEY_PREMISE_DOCUMENT, KEY_MAIN_CONFLICT),
    (KEY_WORLD_LORE_DOCUMENT, KEY_WORLD_LORE),
)
BLOCK_SEPARATOR = "\n\n"
KNOWN_CARD_TYPES = frozenset({"character", "faction", "location", "item"})
OTHER_CARD_TYPE = "other"
NEWBIE_MODE = "newbie"
ENTITY_ALIASES = sa.bindparam("aliases", type_=postgresql.ARRAY(sa.Text()))


def _text_block(text: str) -> dict[str, object]:
    return {"kind": "text", "question_id": None, "label": None, "text": text}


def _one_block_document(text: str) -> dict[str, object]:
    return {"blocks": [_text_block(text)] if text.strip() else []}


def _stakes_document(main_conflict: str) -> dict[str, object]:
    block = {
        "kind": "answer",
        "question_id": STAKES_QUESTION_ID,
        "label": STAKES_LABEL,
        "text": main_conflict,
    }
    return {"blocks": [block]}


def _text_of(value: object) -> str:
    return value if isinstance(value, str) else ""


def _card_entity_type(raw_type: object) -> str:
    card_type = _text_of(raw_type).strip().casefold()
    return card_type if card_type in KNOWN_CARD_TYPES else OTHER_CARD_TYPE


def _insert_card_entities(
    connection: sa.Connection,
    scenario_id: object,
    cards: list[object],
) -> None:
    statement = sa.text(
        "INSERT INTO entities (scenario_id, entity_type, canonical_name, aliases, "
        "description, lore_document) VALUES (:scenario_id, :entity_type, :name, "
        ":aliases, :description, CAST(:lore_document AS jsonb))"
    ).bindparams(ENTITY_ALIASES)
    for raw in cards:
        if not isinstance(raw, dict) or not _text_of(raw.get("name")).strip():
            continue
        name = _text_of(raw.get("name"))
        content = _text_of(raw.get("content"))
        connection.execute(
            statement,
            {
                "scenario_id": scenario_id,
                "entity_type": _card_entity_type(raw.get("type")),
                "name": name,
                "aliases": [name],
                "description": content,
                "lore_document": json.dumps(_one_block_document(content)),
            },
        )


def _migrate_world_data(world_data: dict[str, object]) -> dict[str, object]:
    migrated = {k: v for k, v in world_data.items() if k != KEY_STORY_CARDS}
    main_conflict = _text_of(world_data.get(KEY_MAIN_CONFLICT))
    if main_conflict.strip() and KEY_PREMISE_DOCUMENT not in migrated:
        migrated[KEY_PREMISE_DOCUMENT] = _stakes_document(main_conflict)
        migrated[KEY_PREMISE] = f"{STAKES_LABEL}: {main_conflict.strip()}"
    world_lore = _text_of(world_data.get(KEY_WORLD_LORE))
    if world_lore.strip() and KEY_WORLD_LORE_DOCUMENT not in migrated:
        migrated[KEY_WORLD_LORE_DOCUMENT] = _one_block_document(world_lore)
    return migrated


def _opening_scene_for(row: sa.Row, world_data: dict[str, object]) -> str | None:
    if row.opening_scene and row.opening_scene.strip():
        return row.opening_scene
    opening_prompt = _text_of(world_data.get(KEY_OPENING_PROMPT))
    return opening_prompt if opening_prompt.strip() else row.opening_scene


def _new_persona_document_json(row: sa.Row) -> str | None:
    if row.narrator_persona_document is not None:
        return None
    persona = _text_of(row.narrator_persona)
    return json.dumps(_one_block_document(persona)) if persona.strip() else None


def _migrate_scenario(connection: sa.Connection, row: sa.Row) -> None:
    world_data = json.loads(row.world_data)
    cards = world_data.get(KEY_STORY_CARDS)
    if row.mode == NEWBIE_MODE and isinstance(cards, list):
        _insert_card_entities(connection, row.scenario_id, cards)
    migrated_world_data = _migrate_world_data(world_data)
    opening_scene = _opening_scene_for(row, world_data)
    persona_document = _new_persona_document_json(row)
    is_unchanged = (
        migrated_world_data == world_data
        and opening_scene == row.opening_scene
        and persona_document is None
    )
    if is_unchanged:
        return
    connection.execute(
        sa.text(
            "UPDATE scenarios SET world_data = CAST(:world_data AS jsonb), "
            "opening_scene = :opening_scene, "
            "narrator_persona_document = COALESCE(CAST(:persona_document AS jsonb), "
            "narrator_persona_document) "
            "WHERE scenario_id = :scenario_id"
        ),
        {
            "scenario_id": row.scenario_id,
            "world_data": json.dumps(migrated_world_data),
            "opening_scene": opening_scene,
            "persona_document": persona_document,
        },
    )


def migrate_story_content(connection: sa.Connection) -> None:
    rows = connection.execute(
        sa.text(
            "SELECT scenario_id, mode, world_data::text AS world_data, opening_scene, "
            "narrator_persona, narrator_persona_document::text AS "
            "narrator_persona_document FROM scenarios"
        )
    ).fetchall()
    for row in rows:
        _migrate_scenario(connection, row)


def _card_from_entity(row: sa.Row) -> dict[str, str]:
    return {
        "id": str(row.entity_id),
        "type": row.entity_type,
        "name": row.canonical_name,
        "content": row.description or "",
    }


def restore_story_cards(connection: sa.Connection) -> None:
    scenario_ids = connection.execute(
        sa.text(
            "SELECT DISTINCT entities.scenario_id FROM entities "
            "JOIN scenarios USING (scenario_id) WHERE scenarios.mode = :mode"
        ),
        {"mode": NEWBIE_MODE},
    ).scalars()
    for scenario_id in list(scenario_ids):
        _restore_scenario_cards(connection, scenario_id)


def _read_world_data(
    connection: sa.Connection, scenario_id: object
) -> dict[str, object]:
    raw = connection.execute(
        sa.text("SELECT world_data::text FROM scenarios WHERE scenario_id = :id"),
        {"id": scenario_id},
    ).scalar_one()
    return json.loads(raw)


def _restore_scenario_cards(connection: sa.Connection, scenario_id: object) -> None:
    entities = connection.execute(
        sa.text(
            "SELECT entity_id, entity_type, canonical_name, description "
            "FROM entities WHERE scenario_id = :scenario_id ORDER BY created_at, "
            "canonical_name"
        ),
        {"scenario_id": scenario_id},
    ).fetchall()
    world_data = _read_world_data(connection, scenario_id)
    existing = world_data.get(KEY_STORY_CARDS)
    cards = list(existing) if isinstance(existing, list) else []
    world_data[KEY_STORY_CARDS] = cards + [_card_from_entity(row) for row in entities]
    connection.execute(
        sa.text(
            "UPDATE scenarios SET world_data = CAST(:world_data AS jsonb) "
            "WHERE scenario_id = :scenario_id"
        ),
        {"scenario_id": scenario_id, "world_data": json.dumps(world_data)},
    )
    connection.execute(
        sa.text("DELETE FROM entities WHERE scenario_id = :scenario_id"),
        {"scenario_id": scenario_id},
    )


def _add_scenario_columns() -> None:
    op.add_column(
        "scenarios",
        sa.Column(
            "mood_tags",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
    )
    op.add_column(
        "scenarios",
        sa.Column("narrator_persona_document", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "scenarios",
        sa.Column(
            "player_mode",
            sa.String(length=20),
            server_default="written",
            nullable=False,
        ),
    )
    op.add_column(
        "scenarios",
        sa.Column(
            "guide_seen_features",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        op.f(PLAYER_MODE_CONSTRAINT),
        "scenarios",
        sa.text("player_mode IN ('written', 'player_created')"),
    )


def upgrade() -> None:
    _add_scenario_columns()
    op.add_column(
        "entities", sa.Column("lore_document", postgresql.JSONB(), nullable=True)
    )
    _create_invite_table()
    migrate_story_content(op.get_bind())


def _create_invite_table() -> None:
    _create_invite_table_columns()
    op.create_index("idx_scenario_invites_scenario_id", INVITE_TABLE, ["scenario_id"])


def _create_invite_table_columns() -> None:
    op.create_table(
        INVITE_TABLE,
        sa.Column(
            "invite_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("scenario_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("consumed_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenarios.scenario_id"],
            name=op.f("fk_scenario_invites_scenario_id_scenarios"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.user_id"],
            name=op.f("fk_scenario_invites_created_by_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["consumed_by"],
            ["users.user_id"],
            name=op.f("fk_scenario_invites_consumed_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("invite_id", name=op.f("pk_scenario_invites")),
        sa.UniqueConstraint("token_hash", name="uq_scenario_invites_token_hash"),
    )


def _count(connection: sa.Connection, statement: str) -> int:
    return connection.execute(sa.text(statement)).scalar_one()


def _document_text(document: object) -> str:
    blocks = document.get("blocks") if isinstance(document, dict) else None
    texts = [
        _text_of(block.get("text")).strip()
        for block in (blocks if isinstance(blocks, list) else [])
        if isinstance(block, dict)
    ]
    return BLOCK_SEPARATOR.join(text for text in texts if text)


def _is_document_newer(document: object, legacy_text: str) -> bool:
    if document is None or not legacy_text.strip():
        return False
    return _document_text(document) != legacy_text.strip()


def _count_newer_documents(rows: list[sa.Row]) -> int:
    newer = 0
    for row in rows:
        world_data = json.loads(row.world_data)
        pairs = [
            (world_data.get(document_key), _text_of(world_data.get(legacy_key)))
            for document_key, legacy_key in DOCUMENT_LEGACY_FIELDS
        ]
        pairs.append(
            (
                json.loads(row.narrator_persona_document)
                if row.narrator_persona_document
                else None,
                _text_of(row.narrator_persona),
            )
        )
        newer += sum(_is_document_newer(document, text) for document, text in pairs)
    return newer


def _read_story_rows(connection: sa.Connection) -> list[sa.Row]:
    return connection.execute(
        sa.text(
            "SELECT scenario_id, world_data::text AS world_data, opening_scene, "
            "narrator_persona, narrator_persona_document::text AS "
            "narrator_persona_document FROM scenarios"
        )
    ).fetchall()


def refuse_lossy_downgrade(connection: sa.Connection, rows: list[sa.Row]) -> None:
    newbie_scope = "JOIN scenarios USING (scenario_id) WHERE scenarios.mode = 'newbie'"
    facts = _count(connection, f"SELECT count(*) FROM facts {newbie_scope}")
    if facts:
        raise RuntimeError(
            f"Cannot downgrade: {facts} fact(s) in newbie stories have no place in "
            "the old format. Delete them first."
        )
    players = _count(
        connection,
        f"SELECT count(*) FROM entities {newbie_scope} AND entities.is_player",
    )
    if players:
        raise RuntimeError(
            f"Cannot downgrade: {players} player card(s) in newbie stories would "
            "become ordinary story cards. Delete them first."
        )
    newer = _count_newer_documents(rows)
    if newer:
        raise RuntimeError(
            f"Cannot downgrade: {newer} story document(s) are newer than the "
            "legacy fields and the old Studio would show stale text."
        )


def _legacy_updates(row: sa.Row) -> tuple[dict[str, object], str | None]:
    world_data = json.loads(row.world_data)
    for document_key, legacy_key in DOCUMENT_LEGACY_FIELDS:
        text = _document_text(world_data.get(document_key))
        if text and not _text_of(world_data.get(legacy_key)).strip():
            world_data[legacy_key] = text
    if _text_of(row.opening_scene).strip():
        world_data[KEY_OPENING_PROMPT] = row.opening_scene
    persona = None
    if row.narrator_persona_document and not _text_of(row.narrator_persona).strip():
        persona = _document_text(json.loads(row.narrator_persona_document)) or None
    return world_data, persona


def restore_legacy_fields(connection: sa.Connection, rows: list[sa.Row]) -> None:
    for row in rows:
        world_data, persona = _legacy_updates(row)
        if persona is None and world_data == json.loads(row.world_data):
            continue
        connection.execute(
            sa.text(
                "UPDATE scenarios SET world_data = CAST(:world_data AS jsonb), "
                "narrator_persona = COALESCE(:persona, narrator_persona) "
                "WHERE scenario_id = :scenario_id"
            ),
            {
                "scenario_id": row.scenario_id,
                "world_data": json.dumps(world_data),
                "persona": persona,
            },
        )


def downgrade() -> None:
    connection = op.get_bind()
    rows = _read_story_rows(connection)
    refuse_lossy_downgrade(connection, rows)
    restore_legacy_fields(connection, rows)
    restore_story_cards(connection)
    op.drop_index("idx_scenario_invites_scenario_id", table_name=INVITE_TABLE)
    op.drop_table(INVITE_TABLE)
    op.drop_column("entities", "lore_document")
    op.drop_constraint(op.f(PLAYER_MODE_CONSTRAINT), "scenarios", type_="check")
    op.drop_column("scenarios", "guide_seen_features")
    op.drop_column("scenarios", "player_mode")
    op.drop_column("scenarios", "narrator_persona_document")
    op.drop_column("scenarios", "mood_tags")
