"""Service for restructuring user avatar descriptions into optimal 2D mesh rigging prompts.

Derived from mesh-avatar-studio guidelines:
Head-and-shoulders, front-facing bust, closed mouth, clear eyes, isolated backdrop.

MIT License
Copyright (c) 2026 Yuki Shindo
"""

from __future__ import annotations

DEFAULT_SOVEREIGN_PROMPT = (
    "Front-facing bust portrait of a noble sovereign, head and shoulders visible, "
    "resting closed mouth, clean neutral background."
)

AVATAR_SYSTEM_PROMPT = (
    "You are an expert prompt engineer specializing in 2D character portrait generation for "
    "2.5D mesh rigging (Mesh Avatar Studio / Live2D). "
    "Convert the user's character description into a detailed image generation prompt following these rules: "
    "1. Front-facing bust portrait (head and shoulders visible, centered). "
    "2. Resting closed mouth with clean lip line (no open smiles or teeth showing). "
    "3. Both eyes wide open and clearly visible without heavy hair covering the eyes. "
    "4. Clean, solid or transparent/isolated simple background (no complex background clutter). "
    "5. Crisp lines and defined facial features suitable for texture cutting. "
    "Output ONLY the prompt text."
)


def build_avatar_optimization_instruction(description: str) -> str:
    cleaned = description.strip()
    return (
        f"{AVATAR_SYSTEM_PROMPT}\n\n"
        f"Character Concept: {cleaned}\n"
        f"Ensure: front-facing, head and shoulders, closed mouth, neutral background."
    )


async def optimize_avatar_prompt(description: str) -> str:
    cleaned = description.strip()
    if not cleaned:
        return DEFAULT_SOVEREIGN_PROMPT

    return (
        f"Front-facing bust portrait of {cleaned}, head and shoulders centered in frame, "
        f"resting closed mouth, clean eye contours, crisp lighting, isolated neutral background."
    )
