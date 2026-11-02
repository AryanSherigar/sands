import React from "react";
import type { MapRegion } from "@/shared/types/strategy-map.types";
import type { RegionOutlineLayerProps } from "./RegionOutlineLayer.types";

const TINT_CLASSES = [
  "fill-red-500/25",
  "fill-green-500/25",
  "fill-blue-500/25",
  "fill-yellow-500/25",
  "fill-purple-500/25",
  "fill-orange-500/25",
  "fill-cyan-500/25",
  "fill-pink-500/25",
];
const SELECTED_CLASSES = "stroke-primary stroke-2";
const IDLE_CLASSES = "stroke-white/70 stroke-1";
const NON_SCALING = "[vector-effect:non-scaling-stroke]";

function collectLinks(regions: MapRegion[]): [MapRegion, MapRegion][] {
  const byId = new Map(regions.map((region) => [region.id, region]));
  return regions.flatMap((region) =>
    region.neighbor_ids
      .filter((neighborId) => neighborId > region.id && byId.has(neighborId))
      .map((neighborId): [MapRegion, MapRegion] => [region, byId.get(neighborId) as MapRegion]),
  );
}

function resolveStrokeClass(
  regionId: string,
  selectedIds: string[],
  regionStrokeClasses?: Record<string, string>,
): string {
  if (selectedIds.includes(regionId)) {
    return SELECTED_CLASSES;
  }
  return regionStrokeClasses?.[regionId] ?? IDLE_CLASSES;
}

function renderNeighborLinks(links: [MapRegion, MapRegion][]): React.ReactNode {
  return links.map(([first, second]) => (
    <line
      key={`${first.id}-${second.id}`}
      x1={first.label_point.x}
      y1={first.label_point.y}
      x2={second.label_point.x}
      y2={second.label_point.y}
      className={`pointer-events-none stroke-white/40 stroke-1 ${NON_SCALING}`}
    />
  ));
}

export const RegionOutlineLayer: React.FC<RegionOutlineLayerProps> = ({
  document,
  targetSize,
  selectedIds,
  regionFillClasses,
  regionStrokeClasses,
  showNeighborLinks = false,
  onRegionClick,
}) => {
  const scaleX = targetSize.width / document.width;
  const scaleY = targetSize.height / document.height;
  const links = showNeighborLinks ? collectLinks(document.regions) : [];

  return (
    <g transform={`scale(${scaleX} ${scaleY})`}>
      {document.regions.map((region, index) => {
        const fill = regionFillClasses?.[region.id] ?? TINT_CLASSES[index % TINT_CLASSES.length];
        const stroke = resolveStrokeClass(region.id, selectedIds, regionStrokeClasses);
        return (
          <path
            key={region.id}
            data-region-id={region.id}
            d={region.outline}
            fillRule="evenodd"
            className={`cursor-pointer ${fill} ${NON_SCALING} ${stroke}`}
            onClick={(event) => onRegionClick?.(region.id, event)}
          />
        );
      })}
      {renderNeighborLinks(links)}
    </g>
  );
};
