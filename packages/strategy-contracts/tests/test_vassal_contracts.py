import pytest
from pydantic import ValidationError
from strategy_contracts.enums import OrderKind, RelationStatus
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.publish_checks import IssueCode, check_publishable
from strategy_contracts.scenario import (
    FREE_ORDER_KINDS,
    RelationSetup,
    StrategyScenario,
    Tuning,
)
from strategy_contracts.terms import TermsCard, VassalTerm
from strategy_contracts.vassal import (
    VassalageSetup,
    VassalTier,
    VassalTuning,
    tier_term,
)

FULL_SHARE = 100


def _setup(overlord_id: str = "aa", **overrides: object) -> VassalageSetup:
    return VassalageSetup(
        overlord_id=overlord_id, tribute_share_percent=20, levy_share_percent=0
    ).model_copy(update=overrides)


def test_defaults_load_for_legacy_scenario() -> None:
    assert load_three_crowns().tuning.vassal == VassalTuning()


def test_vassal_term_round_trips() -> None:
    term = VassalTerm(
        overlord_id="aa",
        vassal_id="bb",
        tribute_share_percent=30,
        levy_share_percent=10,
        is_foreign_policy_controlled=True,
        duration_turns=12,
    )

    card = TermsCard.model_validate(
        {
            "proposer_id": "aa",
            "counterpart_id": "bb",
            "terms": [term.model_dump(mode="json")],
        }
    )

    assert card.terms[0] == term


def test_tier_presets_expand_to_the_documented_terms() -> None:
    puppet = tier_term(VassalTier.PUPPET, "aa", "bb")
    tributary = tier_term(VassalTier.TRIBUTARY, "aa", "bb", duration_turns=5)

    assert puppet.levy_share_percent == FULL_SHARE
    assert puppet.is_foreign_policy_controlled and puppet.has_garrison_rights
    assert not tributary.is_foreign_policy_controlled
    assert tributary.duration_turns == 5


def test_share_above_hundred_is_rejected() -> None:
    with pytest.raises(ValidationError):
        VassalTerm(
            overlord_id="aa",
            vassal_id="bb",
            tribute_share_percent=FULL_SHARE + 1,
            levy_share_percent=0,
        )


def test_relation_setup_accepts_a_vassalage_block() -> None:
    relation = RelationSetup(
        faction_a="aa", faction_b="bb", status=RelationStatus.PEACE, vassalage=_setup()
    )

    assert relation.vassalage is not None
    assert relation.vassalage.overlord_id == "aa"


def test_relation_setup_rejects_overlord_outside_the_pair() -> None:
    with pytest.raises(ValidationError):
        RelationSetup(
            faction_a="aa",
            faction_b="bb",
            status=RelationStatus.PEACE,
            vassalage=_setup("cc"),
        )


@pytest.mark.parametrize("status", [RelationStatus.ALLIANCE, RelationStatus.WAR])
def test_relation_setup_rejects_vassalage_between_allied_or_warring_pair(
    status: RelationStatus,
) -> None:
    with pytest.raises(ValidationError):
        RelationSetup(faction_a="aa", faction_b="bb", status=status, vassalage=_setup())


def test_publish_rejects_a_vassal_with_two_overlords() -> None:
    document = load_three_crowns().model_dump(mode="json")
    ids = [faction["id"] for faction in document["factions"]]
    document["starting"]["relations"] = [
        {
            "faction_a": ids[0],
            "faction_b": ids[2],
            "status": "peace",
            "vassalage": _setup(ids[0]).model_dump(mode="json"),
        },
        {
            "faction_a": ids[1],
            "faction_b": ids[2],
            "status": "peace",
            "vassalage": _setup(ids[1]).model_dump(mode="json"),
        },
    ]

    report = check_publishable(StrategyScenario.model_validate(document))

    assert IssueCode.INVALID_VASSALAGE in {issue.code for issue in report.blocking}


def test_publish_rejects_a_vassalage_cycle() -> None:
    document = load_three_crowns().model_dump(mode="json")
    ids = [faction["id"] for faction in document["factions"]]
    document["starting"]["relations"] = [
        {
            "faction_a": ids[0],
            "faction_b": ids[1],
            "status": "peace",
            "vassalage": _setup(ids[0]).model_dump(mode="json"),
        },
        {
            "faction_a": ids[1],
            "faction_b": ids[2],
            "status": "peace",
            "vassalage": _setup(ids[1]).model_dump(mode="json"),
        },
        {
            "faction_a": ids[0],
            "faction_b": ids[2],
            "status": "peace",
            "vassalage": _setup(ids[2]).model_dump(mode="json"),
        },
    ]

    report = check_publishable(StrategyScenario.model_validate(document))

    assert IssueCode.INVALID_VASSALAGE in {issue.code for issue in report.blocking}


def test_strong_cost_below_refuse_cost_is_rejected() -> None:
    with pytest.raises(ValidationError):
        VassalTuning(refuse_opinion_cost=10, strong_opinion_cost=5)


@pytest.mark.parametrize("percent", [0, FULL_SHARE + 1])
def test_rebel_power_percent_outside_one_to_hundred_is_rejected(percent: int) -> None:
    with pytest.raises(ValidationError):
        VassalTuning(rebel_min_power_percent=percent)


def test_new_orders_have_costs_and_free_kinds() -> None:
    costs = Tuning().order_costs

    assert costs[OrderKind.DEMAND_FROM_VASSAL] == 1
    assert costs[OrderKind.ANNEX_VASSAL] == 2
    assert {
        OrderKind.ANSWER_DEMAND,
        OrderKind.GRANT_CONSENT,
        OrderKind.RELEASE_VASSAL,
    } <= FREE_ORDER_KINDS
