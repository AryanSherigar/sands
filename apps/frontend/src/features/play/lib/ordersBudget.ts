import type { CampaignWorldView } from "../types/simulation.types";

export interface OrdersBudget {
  remaining: number;
  spent: number;
  total: number;
}

// NOTE: the simulation exposes no per-turn maximum, so the total is the points
// still unspent plus the cost of orders queued this turn.
export function deriveOrdersBudget(
  world: Pick<CampaignWorldView, "orders_remaining" | "queued_orders" | "turn">,
): OrdersBudget {
  const spent = world.queued_orders
    .filter((queued) => queued.queued_turn === world.turn)
    .reduce((sum, queued) => sum + queued.cost, 0);
  return {
    remaining: world.orders_remaining,
    spent,
    total: world.orders_remaining + spent,
  };
}
