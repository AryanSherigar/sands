import React from "react";
import { Link } from "react-router-dom";
import { useStrategyMap } from "../../hooks/useStrategyMap";
import type { StrategyMapSectionProps } from "./StrategyWorkspace.types";

export const StrategyMapSection: React.FC<StrategyMapSectionProps> = ({ scenarioId }) => {
  const { data: map, isLoading } = useStrategyMap(scenarioId);
  const regionCount = map?.regions.length ?? 0;
  const label = regionCount > 0 ? "Replace the map" : "Import a map";

  return (
    <section className="space-y-2 rounded-md border border-border-subtle bg-surface-raised p-4">
      <h2 className="text-lg font-semibold">1. Map</h2>
      <p className="text-sm text-content-muted">
        {isLoading && "Loading map…"}
        {!isLoading && regionCount === 0 && "No map yet. Upload your map picture and a same-size region-color image."}
        {regionCount > 0 && `${regionCount} regions imported.`}
      </p>
      <Link className="text-sm text-primary underline" to={`/studio/${scenarioId}/region-map`}>
        {label}
      </Link>
    </section>
  );
};
