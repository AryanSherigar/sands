import copy

from scripts.seeding.expr import Cond, Mut, eq, to_condition
from scripts.zegaris.builder import ZegarisScenario, build
from scripts.zegaris.validation import validate

SECRET_WORDS = ("twin", "children", "sun priestess", "immortal", "mimic", "puppet")


def test_the_built_scenario_has_no_problems() -> None:
    assert validate(build()) == []


def _with_encounters(built: ZegarisScenario, encounters: list) -> ZegarisScenario:
    scenario = copy.deepcopy(built.scenario)
    scenario["rules"]["fantasy_combat"]["encounters"] = encounters  # type: ignore[index]
    return ZegarisScenario(**{**built.__dict__, "scenario": scenario})


def test_an_unwinnable_encounter_is_rejected() -> None:
    built = build()
    encounters = copy.deepcopy(built.scenario["rules"]["fantasy_combat"]["encounters"])  # type: ignore[index]
    encounters[-1]["player"]["attack_tags"] = []
    problems = validate(_with_encounters(built, encounters))
    assert any("cannot damage" in item for item in problems)


def test_an_encounter_that_ends_the_story_is_rejected() -> None:
    built = build()
    encounters = copy.deepcopy(built.scenario["rules"]["fantasy_combat"]["encounters"])  # type: ignore[index]
    encounters[0]["outcomes"].append({"id": "x", "kind": "end", "ending_id": "y"})
    problems = validate(_with_encounters(built, encounters))
    assert any("no endings" in item for item in problems)


def test_a_condition_on_an_unknown_field_is_rejected() -> None:
    built = build()
    bad = to_condition(
        Cond(
            "T99 bad",
            eq("world.nowhere", "x"),
            (Mut("world.tithe", "set", "hired"),),
            "",
        )
    )
    problems = validate(
        ZegarisScenario(**{**built.__dict__, "conditions": [*built.conditions, bad]})
    )
    assert problems


def test_nothing_the_client_or_early_narrator_sees_names_a_secret() -> None:
    built = build()
    visible = [
        str(built.scenario["opening_scene"]),
        str(built.scenario["world_data"]),
        str(built.scenario["setup_schema"]),
        str(built.scenario["action_chips"]),
        str(built.scenario["state_schema"]),
        str(built.scenario["narrator_persona"]),
        *(
            f"{seed.payload.description} {seed.payload.narrator_instruction}"
            for seed in built.entities
        ),
    ]
    text = " ".join(visible).lower()
    assert not [word for word in SECRET_WORDS if word in text]
