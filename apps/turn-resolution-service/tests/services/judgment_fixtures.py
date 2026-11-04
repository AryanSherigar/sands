import uuid

from strategy_contracts.judgment import (
    NUANCES_BY_VERDICT,
    AdvisorStance,
    JudgmentOption,
    JudgmentOutcome,
    JudgmentSpec,
    JudgmentSubjectKind,
    JudgmentVerdict,
)
from strategy_contracts.scene import (
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

SCENE_ID = uuid.UUID(int=21)
USER_ID = uuid.UUID(int=22)
EXCHANGE_CAP = 6
HIDDEN_GRUDGE = "Harl's riders burned the granary at Weald Cross."
OPENING_TEXT = (
    "The great iron doors have closed behind the guard company.\n"
    'VEYRA: "Sire, Ashford has bled three seasons of grain."'
)


def judgment_package() -> ScenePackage:
    return ScenePackage(
        scene_id=SCENE_ID,
        initiator=SceneInitiator.AI,
        is_declinable=False,
        playthrough_id=uuid.UUID(int=23),
        scene_type=SceneType.JUDGMENT,
        turn=5,
        situation=SceneSituation(
            summary="Harl, governor of Ash Ford, stands accused before Valdren.",
            facts=[
                SituationFact(label="Accused", value="Harl"),
                SituationFact(
                    label="Charge", value="an uprising in their region has been crushed"
                ),
            ],
        ),
        participants=[
            Participant(
                participant_id="harl",
                kind=ParticipantKind.GOVERNOR,
                name="Harl",
                trait_ids=["proud"],
                trait_notes=["Proud: he will not kneel."],
                mood="hostile",
            ),
            Participant(
                participant_id="veyra",
                kind=ParticipantKind.GOVERNOR,
                name="Veyra",
                trait_notes=["Prudent: she weighs the harvest."],
                stance=AdvisorStance.MERCY,
            ),
            Participant(
                participant_id="brannoch",
                kind=ParticipantKind.OFFICER,
                name="Brannoch",
                stance=AdvisorStance.IRON,
            ),
        ],
        hidden_limits=HiddenLimits(
            grudges=[
                Grudge(
                    id="g1",
                    text=HIDDEN_GRUDGE,
                    source=GrudgeSource.OPINION,
                    band=GrudgeBand.FIRM,
                )
            ]
        ),
        allowed_outcomes=[
            JudgmentSpec(
                subject_kind=JudgmentSubjectKind.GOVERNOR,
                options=[
                    JudgmentOption(
                        verdict=verdict, nuances=list(NUANCES_BY_VERDICT[verdict])
                    )
                    for verdict in JudgmentVerdict
                ],
            )
        ],
        exchange_cap=EXCHANGE_CAP,
        default_outcome=JudgmentOutcome(verdict=JudgmentVerdict.IMPRISON),
    )


def stored_opening() -> SceneExchangeView:
    return SceneExchangeView(sequence=1, player_text="", leader_text=OPENING_TEXT)


def talk(sequence: int) -> SceneExchangeView:
    return SceneExchangeView(
        sequence=sequence,
        player_text=f"player {sequence}",
        leader_text=f"reply {sequence}",
    )


def fetched(
    transcript: list[SceneExchangeView] | None = None,
    status: SceneStatus = SceneStatus.OPENED,
) -> InternalScenePackage:
    history = transcript if transcript is not None else []
    return InternalScenePackage(
        package=judgment_package(),
        status=status,
        transcript=history,
        exchanges_remaining=EXCHANGE_CAP - len(history),
    )
