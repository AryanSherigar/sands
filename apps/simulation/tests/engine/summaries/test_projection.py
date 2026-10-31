from app.engine.summaries.projection import project_summary_fact
from app.models.world_events import EventCause, EventLogEntry, PhaseName
from tests.engine.battles.builders import (
    ATTACKER,
    DEFENDER,
    battle_fixture,
    start_battle,
)
from tests.engine.sieges.builders import (
    BESIEGER,
    TARGET_OWNER,
    TARGET_REGION,
    make_siege_world,
)


def _event(kind: str, subjects: list[str]) -> EventLogEntry:
    return EventLogEntry(
        seq=1,
        turn=0,
        phase=PhaseName.INTERNAL,
        kind=kind,
        cause=EventCause(
            summary_key="DO EVIL",
            subject_ids=subjects,
            inputs={"combat_losses": 12, "enemy_secret": 999, "chance_percent": 40},
        ),
    )


def test_only_own_battle_losses_reach_summary_and_no_raw_summary_key() -> None:
    world, scenario = battle_fixture()
    start_battle(world, scenario)
    own = project_summary_fact(
        world, _event("battle_army_accounted", ["battle_1", "army_a"])
    )
    enemy = project_summary_fact(
        world, _event("battle_army_accounted", ["battle_1", "army_b"])
    )
    assert own is not None and own.values == {"combat_losses": 12}
    assert own.text_key == "battle_army_accounted"
    assert enemy is None


def test_removed_army_uses_event_boundary_ownership() -> None:
    previous, _ = battle_fixture()
    world = previous.model_copy(deep=True)
    del world.armies["army_a"]
    fact = project_summary_fact(
        world, _event("army_supply_disband", ["army_a"]), previous
    )
    assert fact is not None
    assert (
        project_summary_fact(world, _event("army_supply_disband", ["army_b"]), previous)
        is None
    )


def test_stale_region_intelligence_never_grants_current_enemy_event() -> None:
    world, _ = battle_fixture()
    assert (
        project_summary_fact(
            world, _event("regional_unrest_changed", [DEFENDER, "field"])
        )
        is None
    )
    assert (
        project_summary_fact(
            world, _event("faction_war_pressure_changed", [ATTACKER, DEFENDER])
        )
        is None
    )


def _siege_event(kind: str, subjects: list[str]) -> EventLogEntry:
    return EventLogEntry(
        seq=1,
        turn=2,
        phase=PhaseName.SIEGES,
        kind=kind,
        is_major=True,
        cause=EventCause(summary_key=kind, subject_ids=subjects),
    )


def test_a_conquest_involving_the_player_becomes_a_summary_fact() -> None:
    world = make_siege_world()
    event = _siege_event("region_conquered", [BESIEGER, TARGET_OWNER, TARGET_REGION])

    fact = project_summary_fact(world, event)

    assert fact is not None
    assert (fact.kind, fact.region_ids) == ("region_conquered", [TARGET_REGION])


def test_the_player_losing_a_region_is_a_summary_fact_too() -> None:
    world = make_siege_world()
    event = _siege_event("region_occupied", ["house_dunwick", "aldgate"])

    fact = project_summary_fact(world, event)

    assert fact is not None
    assert fact.region_ids == ["aldgate"]


def test_a_siege_between_other_factions_is_not_a_summary_fact() -> None:
    world = make_siege_world()
    event = _siege_event("region_occupied", ["house_dunwick", TARGET_REGION])

    assert project_summary_fact(world, event) is None


def test_siege_progress_is_not_a_summary_fact() -> None:
    event = _siege_event("siege_progressed", [BESIEGER, TARGET_REGION])

    assert project_summary_fact(make_siege_world(), event) is None
