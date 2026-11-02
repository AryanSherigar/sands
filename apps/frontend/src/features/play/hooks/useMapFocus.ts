import { useEffect } from "react";
import type { ReactZoomPanPinchRef } from "react-zoom-pan-pinch";
import type { MapDocument } from "@/shared/types/strategy-map.types";
import {
  MAP_FOCUS_ANIMATION_MS,
  computeFocusTransform,
  findRegionLabelPoint,
} from "../lib/mapFocus";
import { useStrategyPlayStore } from "../stores/strategyPlay.store";

export function useMapFocus(
  mapDoc: MapDocument,
  controls: ReactZoomPanPinchRef | null,
): void {
  const mapFocusTarget = useStrategyPlayStore((state) => state.mapFocusTarget);

  useEffect(() => {
    const wrapper = controls?.instance.wrapperComponent;
    if (!mapFocusTarget || !controls || !wrapper) return;
    const point = findRegionLabelPoint(mapDoc.regions, mapFocusTarget.regionId);
    if (!point) return;
    const viewport = { width: wrapper.offsetWidth, height: wrapper.offsetHeight };
    const { positionX, positionY, scale } = computeFocusTransform(point, viewport);
    controls.setTransform(positionX, positionY, scale, MAP_FOCUS_ANIMATION_MS);
  }, [mapFocusTarget, mapDoc.regions, controls]);
}
