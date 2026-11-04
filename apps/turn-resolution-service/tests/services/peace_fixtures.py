import uuid

from strategy_contracts.peace import PeaceTier
from strategy_contracts.scene import (
    AcceptanceRange,
    CessionOption,
    Grudge,
    GrudgeBand,
    GrudgeSource,
    HiddenLimits,
    Participant,
    ParticipantKind,
    PeaceBrief,
    PeaceTierOption,
    ScenePackage,
    SceneSituation,
    SceneType,
    SituationFact,
    TermsCardOutcome,
    TermsCardSpec,
    TermsResult,
    WarStanding,
)
from strategy_contracts.terms import TermKind

PEACE_GRUDGE = "You raided our granaries."
PEACE_EXCHANGE_CAP = 6
PEACE_WAR_SCORE = 12


def peace_brief(standing: WarStanding = WarStanding.LEADING) -> PeaceBrief:
    return PeaceBrief(
        player_faction_id="house_carrow",
        player_faction_name="Carrow",
        counterpart_faction_id="house_ashford",
        counterpart_faction_name="Ashford",
        standing=standing,
        tiers=[
            PeaceTierOption(tier=PeaceTier.SHORT, turns=6, needs_guarantor=False),
            PeaceTierOption(tier=PeaceTier.GENERATION, turns=60, needs_guarantor=True),
            PeaceTierOption(tier=PeaceTier.PERPETUAL, turns=0, needs_guarantor=True),
        ],
        player_regions=[CessionOption(region_id="elmstead", name="Elmstead")],
        counterpart_regions=[CessionOption(region_id="brennmoor", name="Brennmoor")],
    )


def peace_package(
    standing: WarStanding = WarStanding.LEADING, scene_id: uuid.UUID | None = None
) -> ScenePackage:
    return ScenePackage(
        scene_id=scene_id or uuid.uuid4(),
        playthrough_id=uuid.uuid4(),
        scene_type=SceneType.PEACE,
        turn=5,
        situation=SceneSituation(
            summary="Valdren sues for peace with Mira.",
            facts=[SituationFact(label="Your war score", value=str(PEACE_WAR_SCORE))],
        ),
        participants=[
            Participant(
                participant_id="mira",
                kind=ParticipantKind.LEADER,
                name="Mira of Ashford",
                trait_ids=["proud"],
                mood="hostile",
            )
        ],
        hidden_limits=HiddenLimits(
            acceptance=AcceptanceRange(accept_at=37, haggle_at=21),
            peace_brief=peace_brief(standing),
            grudges=[
                Grudge(
                    id="g1",
                    text=PEACE_GRUDGE,
                    source=GrudgeSource.OPINION,
                    band=GrudgeBand.FIRM,
                )
            ],
        ),
        allowed_outcomes=[
            TermsCardSpec(
                allowed_term_kinds=[TermKind.PEACE, TermKind.PAY_GOLD],
                war_score_available=PEACE_WAR_SCORE,
            )
        ],
        exchange_cap=PEACE_EXCHANGE_CAP,
        default_outcome=TermsCardOutcome(result=TermsResult.REFUSED),
    )
