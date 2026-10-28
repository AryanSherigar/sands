from app.config import settings
from app.models.alpha import AlphaConfigResponse


def build_alpha_config() -> AlphaConfigResponse:
    if not settings.is_alpha_mode:
        return AlphaConfigResponse(
            is_alpha_mode=False,
            is_signup_enabled=True,
            consent_version=None,
            scenario_id=None,
            tension_prompt_every_turns=None,
        )
    return AlphaConfigResponse(
        is_alpha_mode=True,
        is_signup_enabled=settings.is_alpha_signup_enabled,
        consent_version=settings.alpha_consent_version,
        scenario_id=settings.alpha_scenario_id,
        tension_prompt_every_turns=settings.alpha_tension_prompt_every_turns,
    )
