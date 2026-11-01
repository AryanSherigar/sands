from app.engine.letters.arming import arm_letter
from app.engine.letters.constants import LETTER_NO_EFFECT, LETTER_OPTION_IDS
from app.repositories import scene_repo
from app.services.letter_scene import build_letter_package
from app.services.triggered_negotiation import persist_triggered_scene
from strategy_contracts.scene import (
    ChoiceOutcome,
    ChoiceSpec,
    SceneInitiator,
    SceneType,
)
from strategy_contracts.scene_validation import validate_package
from tests.engine.letters.builders import (
    RIVAL_LEADER,
    letter_scenario,
    letter_world,
    set_opinion,
)
from tests.models.builders import PLAYTHROUGH_ID
from tests.repositories.helpers import seed_playthrough


def _armed():
    world = letter_world()
    set_opinion(world, -4)
    world.playthrough_id = PLAYTHROUGH_ID
    scenario = letter_scenario()
    arm_letter(world, scenario)
    return world, scenario


def _package():
    world, scenario = _armed()
    return build_letter_package(
        world,
        scenario,
        world.progress.pending_scene_id,
        world.progress.pending_letter,
    )


def test_package_is_an_ai_declinable_letter_with_two_exchanges() -> None:
    package = _package()
    assert package.scene_type is SceneType.LETTER
    assert package.initiator is SceneInitiator.AI
    assert package.is_declinable is True
    assert package.exchange_cap == 2


def test_package_validates_and_defaults_to_no_effect() -> None:
    package = _package()
    assert validate_package(package) == []
    assert package.default_outcome == ChoiceOutcome(option_id=LETTER_NO_EFFECT)


def test_allowed_outcomes_are_exactly_the_four_fixed_options() -> None:
    spec = _package().allowed_outcomes[0]
    assert isinstance(spec, ChoiceSpec)
    assert tuple(option.id for option in spec.options) == LETTER_OPTION_IDS


def test_the_model_is_offered_ids_and_labels_never_numbers() -> None:
    spec = _package().allowed_outcomes[0]
    for option in spec.options:
        assert not any(character.isdigit() for character in option.label)


def test_participant_is_the_sender_leader_and_topic_is_a_situation_fact() -> None:
    package = _package()
    assert package.participants[0].participant_id == RIVAL_LEADER
    facts = {fact.label: fact.value for fact in package.situation.facts}
    assert facts["Topic"] == "warning"
    assert "Mira" in package.situation.summary


async def test_an_armed_letter_is_persisted_as_a_letter_scene(db_connection) -> None:
    await seed_playthrough(db_connection)
    world, scenario = _armed()

    await persist_triggered_scene(db_connection, world, scenario)

    scene = await scene_repo.get_scene(db_connection, world.progress.pending_scene_id)
    assert scene.package.scene_type is SceneType.LETTER


async def test_persisting_the_same_letter_twice_is_a_no_op(db_connection) -> None:
    await seed_playthrough(db_connection)
    world, scenario = _armed()

    await persist_triggered_scene(db_connection, world, scenario)
    await persist_triggered_scene(db_connection, world, scenario)

    scene = await scene_repo.get_scene(db_connection, world.progress.pending_scene_id)
    assert scene is not None
