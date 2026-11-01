from app.services.pricing import calculate_turn_cost_micros


def test_calculate_turn_cost_gemini_flash() -> None:
    cost = calculate_turn_cost_micros(
        prompt_tokens=1000,
        completion_tokens=500,
        model_name="gemini-2.5-flash",
    )
    assert cost == 450


def test_calculate_turn_cost_with_image_and_audio() -> None:
    cost = calculate_turn_cost_micros(
        prompt_tokens=1000,
        completion_tokens=500,
        model_name="gemini-2.5-flash",
        has_image=True,
        has_audio=True,
    )
    assert cost == 20450


def test_calculate_turn_cost_unknown_model_fallback() -> None:
    cost = calculate_turn_cost_micros(
        prompt_tokens=1000,
        completion_tokens=1000,
        model_name="unknown-model",
    )
    assert cost > 0


def test_calculate_turn_cost_gemini_pro() -> None:
    cost = calculate_turn_cost_micros(
        prompt_tokens=1000,
        completion_tokens=1000,
        model_name="gemini-1.5-pro",
    )
    # 1000 * 1.25 = 1250, 1000 * 5.00 = 5000 -> 6250
    assert cost == 6250


def test_calculate_turn_cost_claude_haiku() -> None:
    cost = calculate_turn_cost_micros(
        prompt_tokens=1000,
        completion_tokens=500,
        model_name="claude-haiku-5-5",
    )
    assert cost == 350


def test_calculate_turn_cost_muse_spark() -> None:
    cost = calculate_turn_cost_micros(
        prompt_tokens=1000, completion_tokens=500, model_name="muse-spark-1.3"
    )
    assert cost == 3375
