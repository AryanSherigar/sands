from app.engine.proclamations.stances import evaluate_minister_stances
from strategy_contracts.proclamation import (
    EstatePillar,
    ProclamationBurden,
    ProclamationDomain,
    ProclamationDraft,
)
from tests.engine.diplomacy.builders import make_world


def test_evaluate_minister_stances_returns_four_ministers() -> None:
    world = make_world()
    draft = ProclamationDraft(
        is_recognized=True,
        domain=ProclamationDomain.MARTIAL_LEVIES,
        burden=ProclamationBurden.MODERATE,
        target_estate=EstatePillar.MILITARY,
        legal_summary="Conscript troops.",
    )
    stances = evaluate_minister_stances(world, draft)
    assert len(stances) == 4
    estates = {m.estate for m in stances}
    assert estates == {
        EstatePillar.NOBILITY,
        EstatePillar.MILITARY,
        EstatePillar.BURGHERS,
        EstatePillar.CLERGY,
    }


def test_marshal_supports_martial_levies() -> None:
    world = make_world()
    draft = ProclamationDraft(
        is_recognized=True,
        domain=ProclamationDomain.MARTIAL_LEVIES,
        burden=ProclamationBurden.MODERATE,
        target_estate=EstatePillar.PEASANTRY
        if hasattr(EstatePillar, "PEASANTRY")
        else EstatePillar.MILITARY,
        legal_summary="Conscript troops.",
    )
    stances = evaluate_minister_stances(world, draft)
    marshal = next(m for m in stances if m.estate is EstatePillar.MILITARY)
    assert marshal.stance in ("support", "cautious")
