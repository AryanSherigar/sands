"""Seed selection: the pure alias matcher and the resolver over a real database."""

from uuid import UUID, uuid4

from app.models.facts import SceneStateRow
from app.services.entity_tagger import build_alias_index
from app.services.seeding import (
    SeedRequest,
    match_aliases,
    order_seed_ids,
    resolve_seeds,
)
from psycopg import AsyncConnection
from tests.repositories import helpers_retrieval as helpers
from tests.services.retrieval_service_helpers import add_entity, add_scene

SEED_CAP = 30
ALIAS_CAP = 5


def index(pairs: list[tuple[str, UUID]]) -> dict[str, set[UUID]]:
    return build_alias_index(pairs)


def test_alias_matches_only_whole_words() -> None:
    mara, cat = uuid4(), uuid4()
    aliases = index([("mara", mara), ("cat", cat)])

    matched = match_aliases("Mara sees a category of catalogues", aliases, ALIAS_CAP)

    assert matched == [mara]


def test_matching_normalizes_case_and_whitespace_and_ignores_punctuation() -> None:
    lord = uuid4()
    aliases = index([("lord vane", lord)])

    assert match_aliases("I greet   LORD\n Vane, warmly.", aliases, ALIAS_CAP) == [lord]
    assert match_aliases("lord vane's hall", aliases, ALIAS_CAP) == [lord]
    assert match_aliases("lordvane", aliases, ALIAS_CAP) == []


def test_matches_are_ordered_by_first_occurrence_in_the_text() -> None:
    first, second = uuid4(), uuid4()
    aliases = index([("orin", second), ("mara", first)])

    assert match_aliases("mara then orin", aliases, ALIAS_CAP) == [first, second]
    assert match_aliases("orin then mara", aliases, ALIAS_CAP) == [second, first]


def test_an_empty_alias_never_matches() -> None:
    aliases = index([("", uuid4())])

    assert match_aliases("anything at all", aliases, ALIAS_CAP) == []


def test_an_ambiguous_alias_seeds_every_entity_up_to_the_cap_deterministically() -> (
    None
):
    many = [UUID(int=number) for number in range(1, 9)]
    aliases = index([("guard", entity_id) for entity_id in many])

    matched = match_aliases("the guard nods", aliases, ALIAS_CAP)

    assert matched == many[:ALIAS_CAP]
    assert match_aliases("the guard nods", aliases, ALIAS_CAP) == matched
    assert match_aliases("the guard nods", aliases, 100) == many


def test_priority_order_is_action_interlocutor_scene_then_recent() -> None:
    action, talker, scene, recent = uuid4(), uuid4(), uuid4(), uuid4()

    ordered = order_seed_ids(
        action_ids=[action],
        interlocutor_ids=[talker],
        scene_ids=[scene],
        recent_ids=[recent],
    )

    assert ordered == [action, talker, scene, recent]


def test_priority_order_deduplicates_keeping_the_highest_priority_slot() -> None:
    shared, other = uuid4(), uuid4()

    ordered = order_seed_ids(
        action_ids=[other],
        interlocutor_ids=[],
        scene_ids=[shared],
        recent_ids=[shared, other],
    )

    assert ordered == [other, shared]


def make_seed_request(world: helpers.World, **overrides: object) -> SeedRequest:
    values: dict[str, object] = {
        "playthrough_id": world.playthrough_id,
        "template_id": world.template_id,
        "action_text": "",
        "recent_text": "",
        "scene_authored_entity_ids": [],
        "interlocutor_authored_entity_id": None,
        "scene": None,
        "seed_cap": SEED_CAP,
        "ambiguous_alias_seed_cap": ALIAS_CAP,
    }
    values.update(overrides)
    return SeedRequest(**values)  # type: ignore[arg-type]


async def seed_names(
    connection: AsyncConnection, world: helpers.World, **overrides: object
) -> list[str]:
    rows = await resolve_seeds(connection, make_seed_request(world, **overrides))
    return [row.canonical_name for row in rows]


async def test_resolver_matches_aliases_in_both_scopes(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    await add_entity(
        db_connection, world.template_scope, "Mara", aliases=("the witch",)
    )
    await add_entity(db_connection, world.playthrough_scope, "Orin")

    names = await seed_names(
        db_connection, world, action_text="I ask THE  Witch about Orin"
    )

    assert names == ["Mara", "Orin"]


async def test_resolver_never_matches_another_playthrough_or_template(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    await add_entity(db_connection, world.sibling_scope, "Mara")
    await add_entity(db_connection, world.foreign_scope, "Mara")
    await add_entity(db_connection, world.other_template_scope, "Mara")

    assert await seed_names(db_connection, world, action_text="Mara") == []


async def test_a_playthrough_without_a_template_reads_playthrough_scope_only(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    await add_entity(db_connection, world.template_scope, "Mara")
    await add_entity(db_connection, world.playthrough_scope, "Orin")

    names = await seed_names(
        db_connection, world, template_id=None, action_text="Mara and Orin"
    )

    assert names == ["Orin"]


async def test_ambiguous_alias_seeds_all_entities_up_to_the_cap(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    for number in range(7):
        await add_entity(
            db_connection,
            world.playthrough_scope,
            f"Guard {number}",
            aliases=("guard",),
        )

    names = await seed_names(db_connection, world, action_text="I hail the guard")

    assert len(names) == ALIAS_CAP


async def test_total_cap_and_priority_across_all_sources(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    await add_entity(db_connection, scope, "Aaa")
    await add_entity(db_connection, scope, "Rrr")
    talker_authored, scene_authored = uuid4(), uuid4()
    await add_entity(
        db_connection, world.template_scope, "Talker", authored_id=talker_authored
    )
    await add_entity(
        db_connection, world.template_scope, "Scenic", authored_id=scene_authored
    )

    kwargs = dict(
        action_text="Aaa",
        recent_text="Rrr",
        interlocutor_authored_entity_id=talker_authored,
        scene_authored_entity_ids=[scene_authored],
    )

    assert await seed_names(db_connection, world, **kwargs) == [
        "Aaa",
        "Talker",
        "Scenic",
        "Rrr",
    ]
    assert await seed_names(db_connection, world, seed_cap=2, **kwargs) == [
        "Aaa",
        "Talker",
    ]
    assert await seed_names(db_connection, world, seed_cap=3, **kwargs) == [
        "Aaa",
        "Talker",
        "Scenic",
    ]


async def test_authored_ids_resolve_in_both_scopes_and_unknown_ids_are_ignored(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    from_template, from_playthrough = uuid4(), uuid4()
    await add_entity(
        db_connection, world.template_scope, "Tmpl", authored_id=from_template
    )
    await add_entity(
        db_connection, world.playthrough_scope, "Overlay", authored_id=from_playthrough
    )
    await add_entity(db_connection, world.sibling_scope, "Alien", authored_id=uuid4())

    names = await seed_names(
        db_connection,
        world,
        scene_authored_entity_ids=[from_playthrough, uuid4(), from_template],
        interlocutor_authored_entity_id=uuid4(),
    )

    assert names == ["Overlay", "Tmpl"]


async def test_an_authored_id_of_another_scope_is_ignored(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    foreign_authored = uuid4()
    await add_entity(
        db_connection, world.foreign_scope, "Alien", authored_id=foreign_authored
    )

    assert (
        await seed_names(
            db_connection, world, scene_authored_entity_ids=[foreign_authored]
        )
        == []
    )


async def test_scene_state_location_and_present_entities_are_seeds(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    tavern = await add_entity(db_connection, scope, "Tavern")
    mara = await add_entity(db_connection, scope, "Mara")
    stranger = await add_entity(db_connection, world.sibling_scope, "Stranger")
    await add_scene(
        db_connection,
        world.playthrough_id,
        5,
        location=tavern.entity_id,
        present=[mara.entity_id, stranger.entity_id],
    )
    scene = SceneStateRow(
        playthrough_id=world.playthrough_id,
        valid_from_seq=5,
        location_entity_id=tavern.entity_id,
        present_entity_ids=[mara.entity_id, stranger.entity_id],
        extraction_batch_id=uuid4(),
    )

    names = await seed_names(db_connection, world, scene=scene)

    assert names == ["Tavern", "Mara"]


async def test_the_player_entity_is_never_seeded_automatically(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    await add_entity(db_connection, scope, "Aria", is_player=True)
    await add_entity(db_connection, scope, "Mara")

    names = await seed_names(db_connection, world, action_text="I greet Mara")

    assert names == ["Mara"]
    assert await seed_names(db_connection, world) == []


async def test_recent_text_matches_rank_after_action_text_matches(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    await add_entity(db_connection, scope, "Orin")
    await add_entity(db_connection, scope, "Mara")

    names = await seed_names(
        db_connection, world, action_text="Mara", recent_text="Orin spoke first"
    )

    assert names == ["Mara", "Orin"]


async def test_pronoun_only_action_seeds_from_recent_text(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    await add_entity(db_connection, world.playthrough_scope, "Mara")

    names = await seed_names(
        db_connection,
        world,
        action_text="I ask her again",
        recent_text="Mara frowned at the door",
    )

    assert names == ["Mara"]
