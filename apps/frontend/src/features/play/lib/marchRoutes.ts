import type { MapRegion, Point } from "@/shared/types/strategy-map.types";
import type { ArmyView, QueuedOrderView } from "../types/simulation.types";

export interface MarchRoute {
  orderId: string;
  points: Point[];
  isPlanned: boolean;
}

function buildPlannedRoutes(
  regions: MapRegion[],
  armies: ArmyView[] | undefined,
  queuedOrders: QueuedOrderView[] | undefined,
): MarchRoute[] {
  const labelPoints = new Map(regions.map((region) => [region.id, region.label_point]));
  const armyLocations = new Map((armies ?? []).map((army) => [army.army_id, army.location_id]));

  return (queuedOrders ?? []).flatMap((queued) => {
    const order = queued.order;
    if (order.kind !== "move_army") return [];
    const regionIds = [
      armyLocations.get(order.army_id),
      ...(order.via_region_ids ?? []),
      order.to_region_id,
    ];
    const points = regionIds.flatMap((regionId) => {
      const point = regionId ? labelPoints.get(regionId) : undefined;
      return point ? [point] : [];
    });
    return points.length >= 2 ? [{ orderId: queued.id, points, isPlanned: true }] : [];
  });
}

function buildActiveRoutes(
  labelPoints: Map<string, Point>,
  armies: ArmyView[] | undefined,
): MarchRoute[] {
  return (armies ?? []).flatMap((army) => {
    const stops = [army.location_id, ...(army.march_route ?? [])];
    const points = stops.flatMap((regionId) => {
      const point = labelPoints.get(regionId);
      return point ? [point] : [];
    });
    return army.march_route && points.length >= 2
      ? [{ orderId: `march-${army.army_id}`, points, isPlanned: false }]
      : [];
  });
}

export function buildMarchRoutes(
  regions: MapRegion[],
  armies: ArmyView[] | undefined,
  queuedOrders: QueuedOrderView[] | undefined,
): MarchRoute[] {
  const labelPoints = new Map(regions.map((region) => [region.id, region.label_point]));
  return [
    ...buildActiveRoutes(labelPoints, armies),
    ...buildPlannedRoutes(regions, armies, queuedOrders),
  ];
}
