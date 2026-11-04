from strategy_contracts.proclamation import (
    ActiveProclamation,
    EstatePillar,
    ProclamationBurden,
    ProclamationDomain,
    ProclamationDraft,
    ProclamationMinisterView,
    ProclamationScenePackage,
)
from strategy_contracts.scene import SceneType


def test_scene_type_includes_proclamation() -> None:
    assert SceneType.PROCLAMATION == "proclamation"


def test_proclamation_domain_enum_values() -> None:
    expected = {
        "martial_levies",
        "emergency_taxation",
        "religious_orthodoxy",
        "noble_privileges",
        "popular_relief",
    }
    assert {d.value for d in ProclamationDomain} == expected


def test_proclamation_burden_enum_values() -> None:
    expected = {"light", "moderate", "severe", "radical"}
    assert {b.value for b in ProclamationBurden} == expected


def test_estate_pillar_enum_values() -> None:
    expected = {"nobility", "military", "burghers", "clergy"}
    assert {e.value for e in EstatePillar} == expected


def test_proclamation_draft_validation() -> None:
    draft = ProclamationDraft(
        is_recognized=True,
        domain=ProclamationDomain.MARTIAL_LEVIES,
        burden=ProclamationBurden.MODERATE,
        target_estate=EstatePillar.MILITARY,
        concession_estate=EstatePillar.BURGHERS,
        legal_summary="Conscript 200 soldiers from the southern marches.",
    )
    assert draft.is_recognized is True
    assert draft.domain is ProclamationDomain.MARTIAL_LEVIES
    assert draft.burden is ProclamationBurden.MODERATE
    assert draft.target_estate is EstatePillar.MILITARY
    assert draft.concession_estate is EstatePillar.BURGHERS


def test_unrecognized_draft_carries_fallback_reason() -> None:
    draft = ProclamationDraft(
        is_recognized=False,
        fallback_reason="incoherent",
        legal_summary="Unrecognized decree",
    )
    assert draft.is_recognized is False
    assert draft.fallback_reason == "incoherent"


def test_active_proclamation_defaults_and_validation() -> None:
    active = ActiveProclamation(
        id="proc_123",
        legal_summary="War silver levy.",
        domain=ProclamationDomain.EMERGENCY_TAXATION,
        burden=ProclamationBurden.SEVERE,
        enacted_turn=3,
        immediate_deltas={"gold": 250, "unrest": 15},
        ongoing_modifiers={"tax_percent_points": 15, "unrest_per_turn": 3},
    )
    assert active.remaining_turns == 4
    assert active.immediate_deltas["gold"] == 250
    assert active.ongoing_modifiers["tax_percent_points"] == 15


def test_legacy_fractional_modifiers_are_dropped_not_rejected() -> None:
    active = ActiveProclamation(
        id="proc_old",
        legal_summary="Old edict.",
        domain=ProclamationDomain.EMERGENCY_TAXATION,
        burden=ProclamationBurden.MODERATE,
        enacted_turn=1,
        immediate_deltas={"gold": 250},
        ongoing_modifiers={"tax_rate_delta": 0.15, "unrest_delta": 3.0},
    )
    assert active.ongoing_modifiers == {}


def test_proclamation_scene_package_structure() -> None:
    draft = ProclamationDraft(
        is_recognized=True,
        domain=ProclamationDomain.NOBLE_PRIVILEGES,
        burden=ProclamationBurden.LIGHT,
        legal_summary="Reaffirm baronial charters.",
    )
    ministers = [
        ProclamationMinisterView(
            estate=EstatePillar.NOBILITY,
            title="Lord Chancellor Morvath",
            stance="support",
            primary_grievance="Baronial liberties",
        ),
        ProclamationMinisterView(
            estate=EstatePillar.MILITARY,
            title="High Marshal Vane",
            stance="cautious",
            primary_grievance="Garrison funding",
        ),
        ProclamationMinisterView(
            estate=EstatePillar.BURGHERS,
            title="Lord Treasurer Hest",
            stance="oppose",
            primary_grievance="Customs exemptions",
        ),
        ProclamationMinisterView(
            estate=EstatePillar.CLERGY,
            title="Arch-Prelate Tomas",
            stance="cautious",
            primary_grievance="Church liberties",
        ),
    ]
    pkg = ProclamationScenePackage(
        scene_id="scene_proc_1",
        draft=draft,
        ministers=ministers,
        exchange_cap=6,
        is_rescinding_previous=False,
    )
    assert len(pkg.ministers) == 4
    assert pkg.draft.domain == ProclamationDomain.NOBLE_PRIVILEGES
