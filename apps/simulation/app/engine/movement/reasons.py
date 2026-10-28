from enum import Enum


class RejectReason(str, Enum):
    UNKNOWN_ARMY = "unknown_army"
    NOT_YOUR_ARMY = "not_your_army"
    FACTION_DESTROYED = "faction_destroyed"
    EMPTY_ARMY = "empty_army"
    COMMANDER_UNAVAILABLE = "commander_unavailable"
    IN_BATTLE = "in_battle"
    UNKNOWN_REGION = "unknown_region"
    ALREADY_THERE = "already_there"
    NO_ROUTE = "no_route"
    AVOID_BLOCKS_GOAL = "avoid_blocks_goal"
    DUPLICATE_ORDER = "duplicate_order"
    TARGET_NOT_HOSTILE = "target_not_hostile"
