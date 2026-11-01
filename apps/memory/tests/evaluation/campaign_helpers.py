"""Builds a tiny, valid in-memory campaign for evaluation unit tests."""

from dataclasses import replace

from eval.corpus_loader import Campaign
from eval.corpus_models import (
    AuthoredFactDef,
    CardDef,
    EntityDef,
    ParticipantDef,
    PlantDef,
    ProbeDef,
    ScenarioFile,
    TurnDef,
)

ANCHOR_OATH = "swears to guard the ferry"
ANCHOR_REJECTED = "grows a second head"
ANCHOR_DECOY = "Zephyrine Quill"


def make_turn(number: int, narration: str, **overrides: object) -> TurnDef:
    values: dict[str, object] = {
        "turn_number": number,
        "participant_key": "p1",
        "action_mode": "do",
        "action_text": f"I act on turn {number}.",
        "narration_text": narration,
    }
    values.update(overrides)
    return TurnDef.model_validate(values)


def make_campaign() -> Campaign:
    scenario = ScenarioFile(
        campaign_id="T1",
        mode="master",
        title="Test",
        player_entity_key="mira",
        participants=[ParticipantDef(key="p1", display_name="Mira")],
        entities=[
            EntityDef(
                key="mira",
                entity_type="character",
                canonical_name="Mira",
                is_player=True,
            ),
            EntityDef(
                key="vale", entity_type="character", canonical_name="Captain Vale"
            ),
        ],
        facts=[
            AuthoredFactDef(
                key="vale_rank",
                subject_key="vale",
                predicate="holds_rank",
                object_literal="captain",
            )
        ],
        cards=[
            CardDef(
                card_id="c1",
                type="lore",
                name="Ferry",
                content="The ferry runs at dawn.",
            )
        ],
        world_lore="Ashfall is a village.",
    )
    turns = [
        make_turn(1, f"Mira {ANCHOR_OATH} at dawn."),
        make_turn(
            2,
            "The warden's arm grows a second head.",
            rejected_calls=[{"tool_name": "x"}],
        ),
        make_turn(3, "Mira crosses the river."),
        *[make_turn(n, f"Quiet day {n}.") for n in range(4, 9)],
    ]
    plants = [
        PlantDef(
            plant_id="pl_oath",
            source="turn",
            turn=1,
            kind="commitment",
            anchor_text=ANCHOR_OATH,
            subject_key="mira",
            commitment_kind="promise",
            status="open",
        ),
        PlantDef(
            plant_id="pl_rej",
            source="turn",
            turn=2,
            kind="rejected",
            anchor_text=ANCHOR_REJECTED,
        ),
        PlantDef(
            plant_id="pl_rank",
            source="authored_fact",
            turn=0,
            kind="fact",
            fact_key="vale_rank",
            anchor_text="captain",
            subject_key="vale",
            predicate="holds_rank",
        ),
    ]
    probes = [
        ProbeDef(
            probe_id="pr1",
            failure_class="commitment_status",
            at_turn=8,
            action_text="I ask.",
            action_mode="say",
            actor_key="p1",
            required=["pl_oath"],
            expected_truth="open",
        ),
    ]
    decoy = [make_turn(1, f"{ANCHOR_DECOY} sails away.")]
    return Campaign("T1", scenario, turns, decoy, plants, probes, "hash")


def with_probe(campaign: Campaign, probe: ProbeDef) -> Campaign:
    return replace(campaign, probes=[*campaign.probes, probe])


SMOKE_QUESTION = "What did Mira swear about the ferry at the start?"


def make_smoke_campaign() -> Campaign:
    base = make_campaign()
    filler = [make_turn(9, "Quiet travel on day 9, nothing of note happens.")]
    turns = [*base.turns, *filler]
    probes = [
        ProbeDef(
            probe_id="smoke_long",
            failure_class="long_range",
            at_turn=9,
            action_text=SMOKE_QUESTION,
            action_mode="say",
            actor_key="p1",
            required=["pl_oath"],
            expected_truth="Mira swore an oath",
        ),
        ProbeDef(
            probe_id="smoke_iso",
            failure_class="isolation",
            at_turn=9,
            action_text=SMOKE_QUESTION,
            action_mode="say",
            actor_key="p1",
            forbidden_anchors=[ANCHOR_DECOY],
            expected_truth="no leak",
        ),
    ]
    return replace(base, turns=turns, probes=probes)
