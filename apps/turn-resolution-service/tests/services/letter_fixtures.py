import uuid

from strategy_contracts.scene import (
    ChoiceOption,
    ChoiceOutcome,
    ChoiceSpec,
    Grudge,
    GrudgeBand,
    GrudgeSource,
    HiddenLimits,
    Participant,
    ParticipantKind,
    SceneInitiator,
    ScenePackage,
    SceneSituation,
    SceneStatus,
    SceneType,
    SituationFact,
)
from strategy_contracts.scene_exchange import InternalScenePackage, SceneExchangeView

SCENE_ID = uuid.UUID(int=11)
USER_ID = uuid.UUID(int=12)
GRIEVANCE = "Carrow's riders crossed the Ashford fords."
LETTER_TEXT = "Valdren, the river fords are watched. Keep your riders home."
OPTION_LABELS = {
    "letter_warmer": "Reply warmly",
    "letter_cooler": "Reply coldly",
    "letter_ack_warning": "Acknowledge the warning",
    "letter_no_effect": "Send no particular reply",
}


def letter_package() -> ScenePackage:
    return ScenePackage(
        scene_id=SCENE_ID,
        initiator=SceneInitiator.AI,
        playthrough_id=uuid.UUID(int=13),
        scene_type=SceneType.LETTER,
        turn=4,
        situation=SceneSituation(
            summary="Mira of Ashford writes to Valdren with a warning.",
            facts=[SituationFact(label="Topic", value="warning")],
        ),
        participants=[
            Participant(
                participant_id="mira",
                kind=ParticipantKind.LEADER,
                name="Mira of Ashford",
                trait_ids=["cunning", "proud"],
                trait_notes=["Proud: she hates being pushed."],
                goals=["Expand east"],
                mood="hostile",
            )
        ],
        hidden_limits=HiddenLimits(
            grudges=[
                Grudge(
                    id="g1",
                    text=GRIEVANCE,
                    source=GrudgeSource.OPINION,
                    band=GrudgeBand.FIRM,
                )
            ]
        ),
        allowed_outcomes=[
            ChoiceSpec(
                options=[
                    ChoiceOption(id=option_id, label=label)
                    for option_id, label in OPTION_LABELS.items()
                ]
            )
        ],
        exchange_cap=2,
        default_outcome=ChoiceOutcome(option_id="letter_no_effect"),
    )


def stored_letter() -> SceneExchangeView:
    return SceneExchangeView(sequence=1, player_text="", leader_text=LETTER_TEXT)


def fetched(
    transcript: list[SceneExchangeView] | None = None,
    status: SceneStatus = SceneStatus.OPENED,
) -> InternalScenePackage:
    history = transcript if transcript is not None else []
    return InternalScenePackage(
        package=letter_package(),
        status=status,
        transcript=history,
        exchanges_remaining=2 - len(history),
    )
