from app.services.proclamation_dialogue_prompt import (
    build_minister_dialogue_prompt,
    build_minister_dialogue_system_prompt,
    build_minister_dialogue_user_prompt,
)
from strategy_contracts.proclamation import (
    ProclamationBurden,
    ProclamationDomain,
    ProclamationDraft,
)


def test_minister_dialogue_prompt_contains_all_four_personas() -> None:
    draft = ProclamationDraft(
        is_recognized=True,
        domain=ProclamationDomain.MARTIAL_LEVIES,
        burden=ProclamationBurden.MODERATE,
        legal_summary="Raise 200 archers.",
    )
    prompt = build_minister_dialogue_prompt(
        draft, turn_context={"is_war": True, "gold": 120}
    )
    assert "Lord Chancellor Morvath" in prompt
    assert "High Marshal Vane" in prompt
    assert "Lord Treasurer Hest" in prompt
    assert "Arch-Prelate Tomas" in prompt


def test_minister_dialogue_system_prompt_has_ad21_prefix_stability() -> None:
    sys1 = build_minister_dialogue_system_prompt()
    sys2 = build_minister_dialogue_system_prompt()
    assert sys1 == sys2
    assert "[CHANCELLOR]:" in sys1
    assert "[MARSHAL]:" in sys1
    assert "[TREASURER]:" in sys1
    assert "[PRELATE]:" in sys1


def test_minister_dialogue_user_prompt_includes_player_speech() -> None:
    draft = ProclamationDraft(
        is_recognized=True,
        domain=ProclamationDomain.EMERGENCY_TAXATION,
        burden=ProclamationBurden.SEVERE,
        legal_summary="Levy high silver.",
    )
    user_prompt = build_minister_dialogue_user_prompt(
        draft,
        turn_context={"turn": 5, "unrest": 40},
        player_speech="The realm must endure whatever the cost.",
    )
    assert "Levy high silver" in user_prompt
    assert "The realm must endure whatever the cost." in user_prompt
