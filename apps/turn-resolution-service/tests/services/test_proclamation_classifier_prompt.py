from app.services.proclamation_classifier_prompt import (
    build_classifier_system_prompt,
    build_classifier_user_prompt,
)


def test_classifier_system_prompt_is_static_and_prefix_stable() -> None:
    s1 = build_classifier_system_prompt()
    s2 = build_classifier_system_prompt()
    assert s1 == s2
    assert "MARTIAL_LEVIES" in s1.upper()
    assert "EMERGENCY_TAXATION" in s1.upper()
    assert "is_recognized" in s1


def test_classifier_user_prompt_formats_sovereign_text() -> None:
    text = "Conscript 300 archers from the south."
    user_prompt = build_classifier_user_prompt(text)
    assert text in user_prompt
    assert "SOVEREIGN TEXT:" in user_prompt
