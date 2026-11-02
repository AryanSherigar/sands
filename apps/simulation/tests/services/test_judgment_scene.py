from app.models.world_character import CommanderState
from app.services.judgment_scene import build_judgment_package, select_advisors
from strategy_contracts.judgment import (
    NUANCES_BY_VERDICT,
    AdvisorStance,
    JudgmentOutcome,
    JudgmentSpec,
    JudgmentSubjectKind,
    JudgmentVerdict,
)
from strategy_contracts.scene import ParticipantKind, SceneInitiator, SceneType
from tests.engine.judgments.builders import (
    GOVERNOR_ID,
    OTHER_GOVERNOR_ID,
    PLAYER,
    RIVAL_LEADER,
    SCENE_ID,
    captive_pending,
    governor_pending,
    judgment_scenario,
    judgment_world,
    mercy_hostage,
)


def _add_commander(world) -> None:
    world.commanders["brannoch"] = CommanderState(
        id="brannoch", name="Brannoch", faction_id=PLAYER
    )


def _package(pending=None, world=None):
    return build_judgment_package(
        world or judgment_world(),
        judgment_scenario(),
        SCENE_ID,
        pending or captive_pending(),
    )


def test_captive_package_offers_four_verdicts_with_four_nuances_each() -> None:
    [spec] = _package().allowed_outcomes
    assert isinstance(spec, JudgmentSpec)
    assert spec.subject_kind is JudgmentSubjectKind.CAPTIVE
    assert [option.verdict for option in spec.options] == list(JudgmentVerdict)
    for option in spec.options:
        assert tuple(option.nuances) == NUANCES_BY_VERDICT[option.verdict]


def test_package_is_an_undeclinable_ai_judgment_that_defaults_to_imprisonment() -> None:
    package = _package()
    assert package.scene_type is SceneType.JUDGMENT
    assert package.initiator is SceneInitiator.AI
    assert package.is_declinable is False
    assert package.exchange_cap == 6
    assert package.default_outcome == JudgmentOutcome(verdict=JudgmentVerdict.IMPRISON)


def test_captive_package_names_the_captive_as_the_accused() -> None:
    package = _package()
    accused = package.participants[0]
    assert accused.name == "Ser Orrin" or accused.participant_id == "ser_orrin"
    assert package.hidden_limits is None


def test_governor_package_names_the_governor_as_the_accused() -> None:
    package = _package(governor_pending())
    accused = package.participants[0]
    assert (accused.participant_id, accused.kind) == (
        GOVERNOR_ID,
        ParticipantKind.GOVERNOR,
    )
    assert package.allowed_outcomes[0].subject_kind is JudgmentSubjectKind.GOVERNOR


def test_hostage_package_names_the_hostage_leader_as_the_accused() -> None:
    world = judgment_world()
    world.prisoners = []
    world.peace.hostages = [mercy_hostage()]
    pending = captive_pending().model_copy(update={"subject_id": "hostage_1"})
    accused = _package(pending, world).participants[0]
    assert (accused.participant_id, accused.kind) == (
        RIVAL_LEADER,
        ParticipantKind.LEADER,
    )


def test_advisors_are_a_mercy_voice_and_an_iron_voice() -> None:
    world = judgment_world()
    _add_commander(world)
    advisors = select_advisors(world, GOVERNOR_ID, judgment_scenario())
    assert [(item.participant_id, item.stance) for item in advisors] == [
        (OTHER_GOVERNOR_ID, AdvisorStance.MERCY),
        ("brannoch", AdvisorStance.IRON),
    ]
    assert advisors[1].kind is ParticipantKind.OFFICER


def test_a_court_of_one_yields_one_advisor_and_an_empty_court_yields_none() -> None:
    world = judgment_world()
    assert [
        item.participant_id
        for item in select_advisors(world, GOVERNOR_ID, judgment_scenario())
    ] == [OTHER_GOVERNOR_ID]
    del world.governors[OTHER_GOVERNOR_ID]
    assert select_advisors(world, GOVERNOR_ID, judgment_scenario()) == []
    assert len(_package(governor_pending(), world).participants) == 1


def test_the_accused_governor_is_never_their_own_advisor() -> None:
    world = judgment_world()
    ids = [
        item.participant_id
        for item in select_advisors(world, GOVERNOR_ID, judgment_scenario())
    ]
    assert GOVERNOR_ID not in ids


def test_participants_are_the_accused_first_then_up_to_two_advisors() -> None:
    world = judgment_world()
    _add_commander(world)
    world.governors["third"] = world.governors[OTHER_GOVERNOR_ID].model_copy(
        update={"id": "third", "opinion_of_ruler": -40}
    )
    package = _package(captive_pending(), world)
    assert len(package.participants) == 3
    assert [item.stance for item in package.participants[1:]] == [
        AdvisorStance.MERCY,
        AdvisorStance.IRON,
    ]
