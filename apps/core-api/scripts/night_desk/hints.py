"""Display hints (tool `status_hud`) for the three visible state fields."""

from scripts.night_desk import prose

CLOCK_START = "23:00"
CLOCK_START_MINUTE_OF_DAY = 23 * 60
CLOCK_GLITCH_BELOW = 25
CLOCK_GLITCH_CHANCE = 0.02
SANITY_CLAMP_MIN = 0
SANITY_CLAMP_MAX = 100
MODERATE_BELOW = 50
CRITICAL_BELOW = 25

SANITY_TIER_MINIMUMS = (75, 50, 25)
TENSION_MOODS = {
    "uneasy": "mystery",
    "tense": "tension",
    "dread": "tension",
    "breaking": "combat",
}


TENSION_TRACKS = {
    tier: f"night-desk-music/{tier}.mp3"
    for tier in ("uneasy", "tense", "dread", "breaking")
}


def clock_hint(glitch_source: str) -> dict[str, object]:
    return {
        "kind": "clock",
        "label": "Shift",
        "start": CLOCK_START,
        "format": "12h",
        "glitch": {
            "source": glitch_source,
            "below": CLOCK_GLITCH_BELOW,
            "chance": CLOCK_GLITCH_CHANCE,
        },
    }


def sanity_hint() -> dict[str, object]:
    names = [tier.name for tier in prose.SANITY_TIERS]
    tiers: list[dict[str, object]] = [
        {"name": name, "min": minimum}
        for name, minimum in zip(names, SANITY_TIER_MINIMUMS, strict=False)
    ]
    tiers.append({"name": names[-1]})
    return {
        "kind": "meter",
        "label": "Sanity",
        "clamp_min": SANITY_CLAMP_MIN,
        "clamp_max": SANITY_CLAMP_MAX,
        "tiers": tiers,
        "effects": {
            "moderate_below": MODERATE_BELOW,
            "critical_below": CRITICAL_BELOW,
        },
    }


def tension_hint() -> dict[str, object]:
    return {
        "kind": "tier",
        "label": "Tension",
        "mood_map": dict(TENSION_MOODS),
        "track_map": dict(TENSION_TRACKS),
    }
