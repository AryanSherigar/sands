from enum import Enum

from app.models.base import WorldModel
from app.models.battle_command import Command
from app.models.orders import Order, QueuedOrder
from strategy_contracts.ids import WholeNumber


class OrderFlag(str, Enum):
    OVER_BUDGET = "over_budget"
    IMPOSSIBLE = "impossible"
    NOT_YOUR_ARMY = "not_your_army"


class QueueOrderRequest(WorldModel):
    order: Order


class QueueOrderResponse(WorldModel):
    queued: QueuedOrder | None = None
    flag: OrderFlag | None = None
    reason: str | None = None
    orders_remaining: int


class CancelOrderResponse(WorldModel):
    refunded: WholeNumber
    orders_remaining: int


class CheckCommandRequest(WorldModel):
    command: Command


class OrderCheckResponse(WorldModel):
    flag: OrderFlag | None = None
    reason: str | None = None
    orders_remaining: int
