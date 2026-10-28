"""Public URLs of a scenario's per-tier music tracks."""

from app.integrations import storage_client
from app.services.display_hints import tier_track_keys


def resolve_tier_track_urls(state_schema: dict[str, object]) -> dict[str, str]:
    return {
        tier: storage_client.public_url_for(object_key)
        for tier, object_key in tier_track_keys(state_schema).items()
    }
