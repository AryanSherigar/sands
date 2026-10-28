import React from "react";
import type { ActiveSituation } from "../../../types/situation.types";

export interface Centroid {
  x: number;
  y: number;
}

export interface StrategySituationPinsProps {
  situations: ActiveSituation[];
  centroids: Record<string, Centroid>;
  onSelectSituation: (situationId: string, regionId: string) => void;
}

export const StrategySituationPins: React.FC<StrategySituationPinsProps> = ({
  situations,
  centroids,
  onSelectSituation,
}) => {
  return (
    <g className="strategy-situation-pins pointer-events-auto">
      {situations.map((sit) => {
        const regionId = sit.regionId;
        const pt = regionId ? centroids[regionId] : undefined;
        if (!regionId || !pt) return null;
        const isHighSeverity = sit.severityStage >= 2;

        return (
          <g
            key={sit.id}
            data-testid={`situation-pin-${regionId}`}
            transform={`translate(${pt.x}, ${pt.y})`}
            className="cursor-pointer group"
            onClick={(e) => {
              e.stopPropagation();
              onSelectSituation(sit.id, regionId);
            }}
          >
            {isHighSeverity && (
              <circle
                r="18"
                className="fill-tertiary/20 animate-ping pointer-events-none"
              />
            )}
            <circle
              r="12"
              className="fill-parchment-panel stroke-tertiary stroke-2 drop-shadow-sm transition-transform group-hover:scale-110"
            />
            <text
              textAnchor="middle"
              dominantBaseline="central"
              className="fill-tertiary text-[10px] font-bold select-none pointer-events-none"
            >
              !
            </text>
          </g>
        );
      })}
    </g>
  );
};
