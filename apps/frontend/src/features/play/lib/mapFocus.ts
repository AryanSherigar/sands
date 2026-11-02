import type { MapRegion, Point } from "@/shared/types/strategy-map.types";

export const MAP_FOCUS_SCALE = 1.5;
export const MAP_FOCUS_ANIMATION_MS = 300;

export interface FocusViewportSize {
  width: number;
  height: number;
}

export interface FocusTransform {
  positionX: number;
  positionY: number;
  scale: number;
}

export function computeFocusTransform(
  point: Point,
  viewport: FocusViewportSize,
  scale: number = MAP_FOCUS_SCALE,
): FocusTransform {
  return {
    positionX: viewport.width / 2 - point.x * scale,
    positionY: viewport.height / 2 - point.y * scale,
    scale,
  };
}

export function findRegionLabelPoint(regions: MapRegion[], regionId: string): Point | null {
  return regions.find((region) => region.id === regionId)?.label_point ?? null;
}
