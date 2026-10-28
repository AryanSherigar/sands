import { describe, it, expect } from "vitest";
import { deriveOrdersBudget } from "../ordersBudget";
import type { QueuedOrderView } from "../../types/simulation.types";

const queued = (id: string, cost: number, queuedTurn: number): QueuedOrderView => ({
  id,
  order: { kind: "halt_army", faction_id: "f1", army_id: "a1" },
  cost,
  queued_turn: queuedTurn,
  is_cancellable: true,
});

describe("deriveOrdersBudget", () => {
  it("adds this turn's queued costs to the remaining points", () => {
    const budget = deriveOrdersBudget({
      turn: 4,
      orders_remaining: 3,
      queued_orders: [queued("a", 1, 4), queued("b", 2, 4)],
    });
    expect(budget).toEqual({ remaining: 3, spent: 3, total: 6 });
  });

  it("ignores orders queued on earlier turns", () => {
    const budget = deriveOrdersBudget({
      turn: 4,
      orders_remaining: 5,
      queued_orders: [queued("a", 2, 3)],
    });
    expect(budget).toEqual({ remaining: 5, spent: 0, total: 5 });
  });
});
