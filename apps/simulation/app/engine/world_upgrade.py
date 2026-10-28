from copy import deepcopy

from app.engine.battle_records import populate_battle_contingents
from app.models.world_battle import BattleStatus
from app.models.world_state import (
    LEGACY_VISIBILITY_RULESET,
    WORLD_SCHEMA_VERSION,
    WorldState,
)

LEGACY_WORLD_SCHEMA_VERSION = 4
PREVIOUS_WORLD_SCHEMA_VERSION = 5
LEGACY_RESOLVED_STATUS = "resolved"


def upgrade_v4_document(document: dict[str, object]) -> WorldState:
    upgraded = deepcopy(document)
    upgraded["schema_version"] = WORLD_SCHEMA_VERSION
    upgraded["visibility_ruleset"] = LEGACY_VISIBILITY_RULESET
    upgraded["battles"] = _upgrade_battles(upgraded)
    upgraded["accepted_commands"] = []
    upgraded["recon_reports"] = {}
    upgraded["scout_missions"] = {}
    upgraded["scout_captures"] = {}
    upgraded["battle_intents"] = {}
    for army in upgraded.get("armies", {}).values():
        army["fatigue"] = 0
    _upgrade_prisoners(upgraded)
    world = WorldState.model_validate(upgraded)
    for battle in world.battles:
        populate_battle_contingents(world, battle)
    return world


def upgrade_v5_document(document: dict[str, object]) -> WorldState:
    upgraded = deepcopy(document)
    upgraded["schema_version"] = WORLD_SCHEMA_VERSION
    upgraded["visibility_ruleset"] = LEGACY_VISIBILITY_RULESET
    return WorldState.model_validate(upgraded)


def _upgrade_battles(document: dict[str, object]) -> list[dict[str, object]]:
    legacy_battles = document.pop("pending_battles", [])
    battles: list[dict[str, object]] = []
    for legacy in legacy_battles:
        battle = dict(legacy)
        battle["created_turn"] = document["clock"]["turn"]
        battle["current_turn"] = document["clock"]["turn"]
        battle["exchanges_used"] = 0
        battle["total_exchanges"] = 0
        battle["status"] = (
            BattleStatus.RESOLVED
            if battle["status"] == LEGACY_RESOLVED_STATUS
            else BattleStatus.AWAITING_COMMANDS
        )
        region = document["regions"].get(battle["region_id"], {})
        battle["region_controller_id"] = region.get("owner_id")
        battles.append(battle)
    return battles


def _upgrade_prisoners(document: dict[str, object]) -> None:
    for prisoner in document.get("prisoners", []):
        if prisoner["kind"] == "troops":
            prisoner["is_legacy_aggregate"] = True
            prisoner["origin_battle_id"] = None
            prisoner["troops_by_type"] = {}
