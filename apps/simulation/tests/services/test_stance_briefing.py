from app.engine.stances.menu import resolve_stance_menu
from app.models.world_character import (
    LeaderState,
    MemoryState,
    OpinionReason,
    OpinionState,
)
from app.models.world_state import WorldState
from app.services.stance_briefing import (
    MAX_BRIEFING_MEMORIES,
    MAX_BRIEFING_OPINIONS,
    build_stance_briefing,
    stance_input_hash,
)
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.traits import TraitAxis, TraitDefinition
from tests.models.builders import make_world

SCENARIO = StrategyScenario.model_validate(
    {
        "custom_traits": [
            TraitDefinition(
                id="warlike",
                name="Warlike",
                description="eager for a fight",
                effects={TraitAxis.AGGRESSION: 3},
            ).model_dump(mode="json")
        ],
        "ambitions": [
            {
                "id": "ambition_crown",
                "name": "Win the crown",
                "condition": {
                    "kind": "comparison",
                    "metric": "turn",
                    "operator": "gte",
                    "value": 1,
                },
            }
        ],
    }
)


def _world() -> WorldState:
    world = make_world()
    world.leaders = {
        "mira": LeaderState(
            id="mira",
            name="Mira",
            faction_id="house_ashford",
            age=40,
            trait_ids=["warlike"],
            ambition_ids=["ambition_crown"],
        ),
        "valdren": LeaderState(
            id="valdren", name="Valdren", faction_id="house_carrow", age=40
        ),
    }
    world.factions["house_ashford"].leader_id = "mira"
    return world


def test_briefing_is_identical_for_identical_worlds() -> None:
    first = build_stance_briefing(_world(), SCENARIO, "mira")
    second = build_stance_briefing(_world(), SCENARIO, "mira")
    assert first == second
    assert stance_input_hash(first) == stance_input_hash(second)


def test_briefing_carries_traits_ambitions_and_current_stance() -> None:
    briefing = build_stance_briefing(_world(), SCENARIO, "mira")
    assert briefing.leader_name == "Mira"
    assert briefing.trait_notes == ["Warlike: eager for a fight"]
    assert briefing.ambitions == ["Win the crown"]
    assert briefing.current_option_id is None


def test_briefing_menu_matches_resolved_menu_order() -> None:
    briefing = build_stance_briefing(_world(), SCENARIO, "mira")
    expected = [stance.id for stance in resolve_stance_menu(SCENARIO, "house_ashford")]
    assert [item.id for item in briefing.menu] == expected


def test_briefing_caps_memories_and_opinions_keeping_the_strongest() -> None:
    world = _world()
    leader = world.leaders["mira"]
    leader.memories = [
        MemoryState(kind=f"event_{turn}", turn=turn, weight=1) for turn in range(9)
    ]
    leader.opinions = {
        f"other_{index}": OpinionState(
            target_id=f"other_{index}",
            reasons=[OpinionReason(cause="x", value=index * 10, fade_per_turn=0)],
        )
        for index in range(6)
    }
    briefing = build_stance_briefing(world, SCENARIO, "mira")
    assert len(briefing.memories) == MAX_BRIEFING_MEMORIES
    assert briefing.memories[-1] == "turn 8: event_8"
    assert len(briefing.opinions) == MAX_BRIEFING_OPINIONS
    assert briefing.opinions[0].startswith("other_5")


def test_input_hash_changes_when_a_memory_is_added() -> None:
    world = _world()
    before = stance_input_hash(build_stance_briefing(world, SCENARIO, "mira"))
    world.leaders["mira"].memories.append(
        MemoryState(kind="betrayal", turn=3, weight=5)
    )
    after = stance_input_hash(build_stance_briefing(world, SCENARIO, "mira"))
    assert before != after


def test_briefing_text_has_no_request_ids_or_timestamps() -> None:
    dumped = build_stance_briefing(_world(), SCENARIO, "mira").model_dump_json()
    assert "stance:" not in dumped
    assert "created_at" not in dumped
