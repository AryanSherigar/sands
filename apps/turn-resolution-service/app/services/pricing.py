"""Unit cost calculation utility for AI operations.

Calculates estimated costs in micro-dollars ($1 = 1,000,000 micros) using
integer math to prevent floating point inaccuracies.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPrice:
    input_micros_per_token: float
    output_micros_per_token: float


_DEFAULT_PRICE = ModelPrice(input_micros_per_token=0.15, output_micros_per_token=0.60)

_MODEL_PRICING: dict[str, ModelPrice] = {
    "gemini-2.5-flash": ModelPrice(0.15, 0.60),
    "gemini-2.0-flash": ModelPrice(0.15, 0.60),
    "gemini-1.5-flash": ModelPrice(0.15, 0.60),
    "gemini-1.5-pro": ModelPrice(1.25, 5.00),
    "claude-haiku-5-5": ModelPrice(0.10, 0.50),
    "muse-spark-1.3": ModelPrice(1.25, 4.25),
}

_IMAGE_GEN_MICROS = 10_000
_AUDIO_GEN_MICROS = 10_000


def calculate_turn_cost_micros(
    prompt_tokens: int,
    completion_tokens: int,
    model_name: str,
    has_image: bool = False,
    has_audio: bool = False,
) -> int:
    """Calculate the estimated total cost in micro-dollars for a turn."""
    price = _MODEL_PRICING.get(model_name, _DEFAULT_PRICE)
    text_micros = int(
        (prompt_tokens * price.input_micros_per_token)
        + (completion_tokens * price.output_micros_per_token)
    )
    image_micros = _IMAGE_GEN_MICROS if has_image else 0
    audio_micros = _AUDIO_GEN_MICROS if has_audio else 0
    return text_micros + image_micros + audio_micros
