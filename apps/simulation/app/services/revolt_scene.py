from uuid import UUID

from app.engine.revolt.options import available_options
from app.models.world_events import PendingRevoltTalk
from app.models.world_internal import UprisingArchetype
from app.models.world_state import WorldState
from app.services.negotiation_scene import _mood
from app.services.scene_package_validation import require_valid_package
from strategy_contracts.revolt import DEFAULT_REVOLT_EXCHANGE_CAP, NO_TERMS_OPTION_ID
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import (
    ChoiceOption,
    ChoiceOutcome,
    ChoiceSpec,
    Participant,
    ParticipantKind,
    SceneInitiator,
    ScenePackage,
    SceneSituation,
    SceneType,
    SituationFact,
)

REGION_LABEL = "Region"
GRIEVANCE_LABEL = "Grievance"
SPOKESPERSON_ID_PREFIX = "spokesperson_"
SPOKESPERSON_NAMES = {
    UprisingArchetype.PETITION: "the guild elder",
    UprisingArchetype.RIOT: "the market crier",
    UprisingArchetype.REBELLION: "the rebel captain",
}
GRIEVANCES = {
    UprisingArchetype.PETITION: "a petition against the burden of taxes",
    UprisingArchetype.RIOT: "a riot over bread and order",
    UprisingArchetype.REBELLION: "an armed rebellion against the crown",
}
SUMMARY = "{speaker} of {region} stands before {ruler} to speak for the people."


def _region_name(region_id: str) -> str:
    return region_id.replace("_", " ").title()


def _spokesperson(world: WorldState, pending: PendingRevoltTalk) -> Participant:
    unrest = world.regions[pending.region_id].unrest
    return Participant(
        participant_id=f"{SPOKESPERSON_ID_PREFIX}{pending.region_id}",
        kind=ParticipantKind.LEADER,
        name=SPOKESPERSON_NAMES[pending.archetype].title(),
        mood=_mood(-unrest),
    )


def build_revolt_talk_package(
    world: WorldState,
    scenario: StrategyScenario,
    scene_id: UUID,
    pending: PendingRevoltTalk,
) -> ScenePackage:
    speaker = _spokesperson(world, pending)
    options = [
        ChoiceOption(id=option.id, label=option.label)
        for option in available_options(world, scenario, pending)
    ]
    package = ScenePackage(
        scene_id=scene_id,
        initiator=SceneInitiator.PLAYER,
        is_declinable=True,
        playthrough_id=world.playthrough_id,
        scene_type=SceneType.REVOLT_TALK,
        turn=world.clock.turn,
        situation=SceneSituation(
            summary=SUMMARY.format(
                speaker=speaker.name,
                region=_region_name(pending.region_id),
                ruler=world.ruler.name,
            ),
            facts=[
                SituationFact(
                    label=REGION_LABEL, value=_region_name(pending.region_id)
                ),
                SituationFact(
                    label=GRIEVANCE_LABEL, value=GRIEVANCES[pending.archetype]
                ),
            ],
        ),
        participants=[speaker],
        allowed_outcomes=[ChoiceSpec(options=options)],
        exchange_cap=DEFAULT_REVOLT_EXCHANGE_CAP,
        default_outcome=ChoiceOutcome(option_id=NO_TERMS_OPTION_ID),
    )
    return require_valid_package(package)
