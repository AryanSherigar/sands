"""Token usage dataclass for tracking LLM consumption per turn."""

from dataclasses import dataclass


@dataclass
class TokenUsage:
    """Carries token count and model attribution for an AI operation."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    model_name: str = ""

    @property
    def total_tokens(self) -> int:
        """Sum of prompt and completion tokens."""
        return self.prompt_tokens + self.completion_tokens
