import uuid

from strategy_contracts.revolt import NO_TERMS_OPTION_ID
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

REVOLT_PLAYTHROUGH_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
REVOLT_EXCHANGE_CAP = 4
REVOLT_OPTION_IDS = (
    NO_TERMS_OPTION_ID,
    "tax_relief",
    "garrison_out",
    "relief_small",
    "relief_large",
    "amnesty",
    "charter",
)
REVOLT_LABELS = {
    NO_TERMS_OPTION_ID: "Offer nothing but words",
    "tax_relief": "Lower the taxes",
    "garrison_out": "Keep soldiers out of the region",
    "relief_small": "Open the granaries a little",
    "relief_large": "Pay a great relief",
    "amnesty": "Pardon the rebels",
    "charter": "Grant a charter: lower taxes and no soldiers",
}


def revolt_package(scene_id: uuid.UUID | None = None) -> ScenePackage:
    return ScenePackage(
        scene_id=scene_id or uuid.uuid5(REVOLT_PLAYTHROUGH_ID, "revolt"),
        initiator=SceneInitiator.PLAYER,
        is_declinable=True,
        playthrough_id=REVOLT_PLAYTHROUGH_ID,
        scene_type=SceneType.REVOLT_TALK,
        turn=4,
        situation=SceneSituation(
            summary="The Guild Elder of Home stands before King Alden to speak for the people.",
            facts=[
                SituationFact(label="Region", value="Home"),
                SituationFact(
                    label="Grievance", value="a petition against the burden of taxes"
                ),
            ],
        ),
        participants=[
            Participant(
                participant_id="spokesperson_home",
                kind=ParticipantKind.LEADER,
                name="The Guild Elder",
                mood="hostile",
            )
        ],
        allowed_outcomes=[
            ChoiceSpec(
                options=[
                    ChoiceOption(id=option_id, label=REVOLT_LABELS[option_id])
                    for option_id in REVOLT_OPTION_IDS
                ]
            )
        ],
        exchange_cap=REVOLT_EXCHANGE_CAP,
        default_outcome=ChoiceOutcome(option_id=NO_TERMS_OPTION_ID),
    )
