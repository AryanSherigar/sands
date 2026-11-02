import { describe, expect, it } from "vitest";
import { DEFAULT_PREVIEW_WORLD } from "../../components/StrategyPlayScreen/defaultPreviewWorld";
import { adaptHistoricalWorld } from "../historicalWorld";

describe("adaptHistoricalWorld", () => {
  it("builds a quiet read-only world for a past turn", () => {
    const { turn: _t, world_version: _v, status: _s, wave: _w, ...worldView } = DEFAULT_PREVIEW_WORLD;
    const world = adaptHistoricalWorld({
      turn: 3,
      world_hash: "abc123",
      world: {
        ...worldView,
        pending_events: [{ id: "e1" }],
        queued_orders: [{ id: "q1" }],
        battles: [{ id: "b1" }],
      },
    });

    expect(world.turn).toBe(3);
    expect(world.world_hash).toBe("abc123");
    expect(world.status).toBe("turn_completed");
    expect(world.pending_events).toEqual([]);
    expect(world.queued_orders).toEqual([]);
    expect(world.battles).toEqual([]);
    expect(world.regions.length).toBe(DEFAULT_PREVIEW_WORLD.regions.length);
  });
});
