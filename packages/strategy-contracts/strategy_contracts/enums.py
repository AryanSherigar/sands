from enum import Enum


class Terrain(str, Enum):
    PLAIN = "plain"
    HILLS = "hills"
    MOUNTAIN = "mountain"
    FOREST = "forest"
    MARSH = "marsh"
    DESERT = "desert"
    COAST = "coast"


class TroopType(str, Enum):
    INFANTRY = "infantry"
    CAVALRY = "cavalry"
    ARCHERS_SIEGE = "archers_siege"


class RelationStatus(str, Enum):
    WAR = "war"
    PEACE = "peace"
    ALLIANCE = "alliance"


class OrdersMode(str, Enum):
    BUDGET = "budget"
    UNLIMITED = "unlimited"
    ARMIES_FREE = "armies_free"


class PayLevel(str, Enum):
    FULL = "full"
    REDUCED = "reduced"


class TaxRate(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class ImprovementKind(str, Enum):
    FARMS_AND_MARKET = "farms_and_market"
    FORT = "fort"
    BARRACKS = "barracks"
    ROADS = "roads"
    TEMPLE = "temple"


class OrderKind(str, Enum):
    MAP_SCOUT = "map_scout"
    MOVE_ARMY = "move_army"
    HALT_ARMY = "halt_army"
    ATTACK = "attack"
    BESIEGE = "besiege"
    RAISE_ARMY = "raise_army"
    DISBAND_ARMY = "disband_army"
    MERGE_ARMIES = "merge_armies"
    SPLIT_ARMY = "split_army"
    SET_PAY = "set_pay"
    SET_TAX_RATE = "set_tax_rate"
    TAKE_LOAN = "take_loan"
    DECLARE_DEFAULT = "declare_default"
    BUILD_IMPROVEMENT = "build_improvement"
    DIPLOMATIC_PLAY = "diplomatic_play"
    PROPOSE_AGREEMENT = "propose_agreement"
    SEND_ENVOY = "send_envoy"
    HANDLE_PRISONER = "handle_prisoner"
    MEDIATE = "mediate"
    ANSWER_CALL = "answer_call"
    DENOUNCE_ALLIANCE = "denounce_alliance"
    DEMAND_FROM_VASSAL = "demand_from_vassal"
    ANSWER_DEMAND = "answer_demand"
    GRANT_CONSENT = "grant_consent"
    RELEASE_VASSAL = "release_vassal"
    ANNEX_VASSAL = "annex_vassal"
    ANSWER_EVENT = "answer_event"
    DECLARE_WAR = "declare_war"
    CALL_NEGOTIATION = "call_negotiation"
    FABRICATE_CLAIM = "fabricate_claim"


class RouteStyle(str, Enum):
    FASTEST = "fastest"
    SAFEST = "safest"
    ROADS = "roads"
