import React from "react";
import type { MarchRoute } from "../../../lib/marchRoutes";

export interface MarchRouteLayerProps {
  routes: MarchRoute[];
}

const ARROW_MARKER_ID = "march-route-arrow";

export const MarchRouteLayer: React.FC<MarchRouteLayerProps> = ({ routes }) => {
  if (routes.length === 0) return null;

  return (
    <g aria-label="Planned marches" className="pointer-events-none">
      <defs>
        <marker
          id={ARROW_MARKER_ID}
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#7A2E1D" />
        </marker>
      </defs>
      {routes.map((route) => (
        <polyline
          key={route.orderId}
          data-testid="march-route"
          points={route.points.map((point) => `${point.x},${point.y}`).join(" ")}
          fill="none"
          stroke="#7A2E1D"
          strokeWidth={route.isPlanned ? 3 : 4}
          strokeDasharray={route.isPlanned ? "10 8" : undefined}
          opacity={route.isPlanned ? 1 : 0.85}
          strokeLinecap="round"
          strokeLinejoin="round"
          markerEnd={`url(#${ARROW_MARKER_ID})`}
        />
      ))}
    </g>
  );
};
