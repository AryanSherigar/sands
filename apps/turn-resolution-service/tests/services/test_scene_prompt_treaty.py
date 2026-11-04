import uuid

from app.services import scene_prompt, scene_prompt_peace
from app.services.scene_prompt_treaty import is_treaty_package, verdict_hint
from strategy_contracts.scene import (
    AcceptanceRange,
    HiddenLimits,
    Participant,
    ParticipantKind,
    ScenePackage,
    SceneSituation,
    SceneType,
    SituationFact,
    TermsCardOutcome,
    TermsCardSpec,
    TermsResult,
)
from strategy_contracts.scene_exchange import SceneExchangeView
from strategy_contracts.terms import TermKind
from strategy_contracts.treaty import Verdict
from tests.turn.prefix_stability import assert_shared_through

ACCEPT_AT = 83
HAGGLE_AT = 63
TREATY_KINDS = [
    TermKind.NON_AGGRESSION,
    TermKind.TRADE_DEAL,
    TermKind.MILITARY_ACCESS,
    TermKind.PAY_GOLD,
    TermKind.TRIBUTE,
    TermKind.ALLIANCE,
    TermKind.VASSAL,
    TermKind.SWORN_PROMISE,
]


def _package(
    accept_at: int = ACCEPT_AT,
    kinds: list[TermKind] | None = None,
) -> ScenePackage:
    return ScenePackage(
        scene_id=uuid.uuid4(),
        playthrough_id=uuid.uuid4(),
        scene_type=SceneType.NEGOTIATION,
        turn=3,
        situation=SceneSituation(
            summary="Valdren seeks a treaty with Mira.",
            facts=[
                SituationFact(label="Your realm id", value="house_ashford"),
                SituationFact(label="The player's realm id", value="house_carrow"),
            ],
        ),
        participants=[
            Participant(
                participant_id="mira",
                kind=ParticipantKind.LEADER,
                name="Mira of Ashford",
                trait_ids=["cunning"],
            )
        ],
        hidden_limits=HiddenLimits(
            acceptance=AcceptanceRange(
                accept_at=accept_at, haggle_at=min(HAGGLE_AT, accept_at)
            ),
        ),
        allowed_outcomes=[
            TermsCardSpec(
                allowed_term_kinds=kinds or TREATY_KINDS,
                price_by_term_kind={TermKind.NON_AGGRESSION: 6},
                max_duration_turns=12,
            )
        ],
        exchange_cap=6,
        default_outcome=TermsCardOutcome(result=TermsResult.REFUSED),
    )


def _exchange(
    verdict: Verdict | None, player_text: str = "Pact and trade."
) -> SceneExchangeView:
    return SceneExchangeView(
        sequence=1, player_text=player_text, leader_text="Maybe.", verdict=verdict
    )


def _render(system: str, contents) -> str:
    parts = [system] + [
        f"{item.role}: {part.text}" for item in contents for part in item.parts
    ]
    return "\n".join(parts)


def test_multi_clause_packages_are_recognised() -> None:
    legacy = _package(kinds=[TermKind.NON_AGGRESSION, TermKind.SWORN_PROMISE])

    assert is_treaty_package(_package()) is True
    assert is_treaty_package(legacy) is False


def test_the_treaty_profile_replaces_the_pact_only_rules() -> None:
    system = scene_prompt.build_system_instruction(_package())

    assert "trade deal" in system
    assert "military access" in system
    assert "Never invent" in system
    assert "only to a non-aggression pact or to a sworn promise" not in system


def test_the_decision_directive_lists_a_shape_for_every_clause_kind() -> None:
    profile = scene_prompt.profile_for_package(_package())

    for kind in TREATY_KINDS:
        assert kind.value in profile.decision_directive
    assert '"terms"' in profile.decision_directive
    assert "cited_grudge_ids" in profile.decision_directive


def test_the_brief_names_both_realm_ids_and_a_stance_without_numbers() -> None:
    system = scene_prompt.build_system_instruction(_package())
    brief = system.split("PRIVATE BRIEF")[1]

    assert "house_ashford" in system and "house_carrow" in system
    assert str(ACCEPT_AT) not in system and str(HAGGLE_AT) not in system
    assert "turns or longer" not in brief


def test_the_stance_follows_how_demanding_the_limits_are() -> None:
    eager = scene_prompt.build_system_instruction(_package(accept_at=10))
    hostile = scene_prompt.build_system_instruction(_package(accept_at=200))

    assert eager.split("PRIVATE BRIEF")[1] != hostile.split("PRIVATE BRIEF")[1]


def test_a_bargaining_verdict_becomes_a_hint_in_the_final_turn_only() -> None:
    package = _package()
    profile = scene_prompt.profile_for_package(package)
    system = scene_prompt.build_system_instruction(package)
    contents = scene_prompt.build_reply_contents(
        [_exchange(Verdict.HAGGLE)], "Add trade.", 6, profile=profile
    )

    hint = verdict_hint(Verdict.HAGGLE)
    assert hint is not None and hint in contents[-1].parts[0].text
    assert hint not in system
    assert all(hint not in part.text for item in contents[:-1] for part in item.parts)


def test_accepted_or_missing_verdicts_add_no_hint() -> None:
    assert verdict_hint(Verdict.ACCEPT) is None
    assert verdict_hint(None) is None


def test_consecutive_treaty_exchanges_share_the_head() -> None:
    package = _package()
    profile = scene_prompt.profile_for_package(package)
    system = scene_prompt.build_system_instruction(package)
    first = scene_prompt.build_reply_contents([], "Let us talk.", 6, profile=profile)
    second = scene_prompt.build_reply_contents(
        [_exchange(Verdict.REFUSE, "Let us talk.")], "Again.", 6, profile=profile
    )

    assert_shared_through(
        _render(system, first), _render(system, second), "</player_says>"
    )


def test_no_prompt_ever_carries_the_hidden_limits() -> None:
    package = _package()
    profile = scene_prompt.profile_for_package(package)
    system = scene_prompt.build_system_instruction(package)
    reply = scene_prompt.build_reply_contents(
        [_exchange(Verdict.HAGGLE)], "x", 6, profile=profile
    )
    decision = scene_prompt.build_decision_contents(
        [_exchange(Verdict.HAGGLE)], "x", "y", 6, profile=profile
    )

    text = _render(system, reply + decision)
    assert str(ACCEPT_AT) not in text
    assert str(HAGGLE_AT) not in text


def test_the_peace_menu_now_offers_tribute_and_trade() -> None:
    directive = scene_prompt_peace.PEACE_DECISION_DIRECTIVE

    assert "tribute" in directive and "trade_deal" in directive
    assert "tribute" in scene_prompt_peace.PEACE_RULES


def test_decision_directive_teaches_conditional_clauses() -> None:
    from app.services.scene_prompt_treaty import TREATY_DECISION_DIRECTIVE
    from strategy_contracts.condition_templates import ConditionTemplate

    assert '"kind": "conditional"' in TREATY_DECISION_DIRECTIVE
    for template in ConditionTemplate:
        assert template.value in TREATY_DECISION_DIRECTIVE


def test_the_ruler_may_not_demand_more_gold_than_the_player_holds() -> None:
    system = scene_prompt.build_system_instruction(_package())

    assert "treasury" in system
    assert "more gold than" in system


def test_a_bargaining_hint_covers_terms_the_player_cannot_afford() -> None:
    hint = verdict_hint(Verdict.HAGGLE)

    assert hint is not None and "afford" in hint
