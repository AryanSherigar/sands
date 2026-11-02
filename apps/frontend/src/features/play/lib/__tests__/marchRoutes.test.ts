import { describe, expect, it } from "vitest";
import type { MapRegion } from "@/shared/types/strategy-map.types";
import type { QueuedOrderView } from "../../types/simulation.types";
import { buildMarchRoutes } from "../marchRoutes";

const region = (id: string, x: number): MapRegion => ({
  id,
  name: id,
  terrain: "plain",
  outline: "M 0 0 Z",
  label_point: { x, y: 10 },
  neighbor_ids: [],
  source_color: null,
  source_ref: null,
});

const REGIONS = [region("a", 10), region("b", 20), region("c", 30)];
const ARMIES = [{ army_id: "army-1", owner_id: "me", location_id: "a" }];

const moveOrder = (via?: string[]): QueuedOrderView => ({
  id: "q1",
  cost: 1,
  queued_turn: 1,
  is_cancellable: true,
  order: { kind: "move_army", faction_id: "me", army_id: "army-1", to_region_id: "c", via_region_ids: via },
});

describe("buildMarchRoutes", () => {
  it("draws from the army's location through via regions to the destination", () => {
    const [route] = buildMarchRoutes(REGIONS, ARMIES, [moveOrder(["b"])]);

    expect(route?.points.map((point) => point.x)).toEqual([10, 20, 30]);
  });

  it("ignores non-move orders and armies with unknown locations", () => {
    const halt: QueuedOrderView = {
      ...moveOrder(),
      order: { kind: "halt_army", faction_id: "me", army_id: "army-1" },
    };

    expect(buildMarchRoutes(REGIONS, ARMIES, [halt])).toEqual([]);
    expect(buildMarchRoutes(REGIONS, [], [moveOrder()])).toEqual([]);
  });

  it("draws a moving army's live route as a solid march", () => {
    const moving = [{ ...ARMIES[0]!, march_route: ["b", "c"] }];

    const [route] = buildMarchRoutes(REGIONS, moving, []);

    expect(route?.isPlanned).toBe(false);
    expect(route?.points.map((point) => point.x)).toEqual([10, 20, 30]);
  });

  it("marks queued orders as planned", () => {
    const [route] = buildMarchRoutes(REGIONS, ARMIES, [moveOrder()]);

    expect(route?.isPlanned).toBe(true);
  });
});
