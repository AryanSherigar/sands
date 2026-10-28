import hashlib
import json

from app.models.world_state import WorldState


def canonical_world_json(world: WorldState) -> str:
    document = world.model_dump(mode="json")
    # NOTE: an absent epithet is left out so worlds recorded before the field existed keep their hashes.
    if document["ruler"].get("epithet") is None:
        document["ruler"].pop("epithet", None)
    return json.dumps(document, sort_keys=True, separators=(",", ":"))


def world_hash(world: WorldState) -> str:
    return hashlib.sha256(canonical_world_json(world).encode("utf-8")).hexdigest()
