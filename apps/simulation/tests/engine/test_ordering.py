from app.engine.ordering import canonicalize_lists, sorted_items

from tests.models.builders import make_relation, make_world


def test_sorted_items_orders_by_key() -> None:
    assert sorted_items({"b": 2, "a": 1, "c": 3}) == [("a", 1), ("b", 2), ("c", 3)]


def test_canonicalize_sorts_relations_by_pair() -> None:
    world = make_world()
    world.relations = [
        make_relation("house_carrow", "house_dunwick"),
        make_relation("house_ashford", "house_dunwick"),
        make_relation("house_ashford", "house_carrow"),
    ]
    canonicalize_lists(world)
    assert [(r.faction_a, r.faction_b) for r in world.relations] == [
        ("house_ashford", "house_carrow"),
        ("house_ashford", "house_dunwick"),
        ("house_carrow", "house_dunwick"),
    ]


def test_canonicalize_is_idempotent() -> None:
    world = make_world()
    world.relations = [
        make_relation("house_carrow", "house_dunwick"),
        make_relation("house_ashford", "house_carrow"),
    ]
    canonicalize_lists(world)
    once = world.model_dump()
    canonicalize_lists(world)
    assert world.model_dump() == once
