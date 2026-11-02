from app.models.world_character import CommanderState
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from app.services.prisoner_projection import project_prisoners
from tests.engine.judgments.builders import (
    CAPTIVE_CHARACTER,
    CAPTIVE_ID,
    PLAYER,
    RIVAL,
    TURN,
    judgment_scenario,
    judgment_world,
)


def test_a_held_noble_projects_with_name_title_and_ransom_value() -> None:
    world = judgment_world()
    world.commanders[CAPTIVE_CHARACTER] = CommanderState(
        id=CAPTIVE_CHARACTER, name="Ser Orrin", faction_id=RIVAL
    )
    scenario = judgment_scenario()
    [view] = project_prisoners(world, scenario, PLAYER)
    assert (view.id, view.name, view.title) == (CAPTIVE_ID, "Ser Orrin", "Commander")
    assert view.origin_faction_id == RIVAL
    assert view.ransom_value_gold == scenario.tuning.peace.ransom_gold_per_character
    assert view.sentence_ends_turn is None


def test_a_noble_without_a_known_record_still_projects_a_name() -> None:
    [view] = project_prisoners(judgment_world(), judgment_scenario(), PLAYER)
    assert (view.name, view.title) == ("Ser Orrin", "Noble")


def test_a_sentence_is_projected() -> None:
    world = judgment_world()
    world.prisoners[0].sentence_ends_turn = TURN + 6
    [view] = project_prisoners(world, judgment_scenario(), PLAYER)
    assert view.sentence_ends_turn == TURN + 6


def test_troop_captives_and_prisoners_held_by_others_are_not_projected() -> None:
    world = judgment_world()
    world.prisoners.append(
        PrisonerState(
            id="held_by_ai",
            held_by_id=RIVAL,
            origin_faction_id=PLAYER,
            kind=PrisonerKind.CHARACTER,
            character_id="ser_other",
        )
    )
    assert [
        item.id for item in project_prisoners(world, judgment_scenario(), PLAYER)
    ] == [CAPTIVE_ID]
