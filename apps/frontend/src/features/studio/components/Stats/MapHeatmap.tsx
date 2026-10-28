import React from "react";
import { HEATMAP_PIN_RADIUS, HEATMAP_VIEWBOX_SIZE } from "../../constants/stats";
import { pinOpacity } from "../../lib/chartGeometry";
import type { MapHeatmapProps } from "./MapHeatmap.types";

export const MapHeatmap: React.FC<MapHeatmapProps> = ({ map, ariaLabel }) => (
  <svg
    viewBox={`0 0 ${HEATMAP_VIEWBOX_SIZE} ${HEATMAP_VIEWBOX_SIZE}`}
    preserveAspectRatio="none"
    role="img"
    aria-label={ariaLabel}
    className="aspect-video w-full rounded-lg bg-surface-raised"
  >
    {map.image_url && (
      <image
        href={map.image_url}
        x={0}
        y={0}
        width={HEATMAP_VIEWBOX_SIZE}
        height={HEATMAP_VIEWBOX_SIZE}
        preserveAspectRatio="none"
      />
    )}
    {map.pins.map((pin) => (
      <circle
        key={pin.entity_id}
        cx={pin.x * HEATMAP_VIEWBOX_SIZE}
        cy={pin.y * HEATMAP_VIEWBOX_SIZE}
        r={HEATMAP_PIN_RADIUS}
        fillOpacity={pinOpacity(pin.discovery_rate)}
        strokeWidth={0.3}
        className="fill-accent stroke-content"
      />
    ))}
  </svg>
);
