import React from "react";
import { Link } from "react-router-dom";
import { isMapJobActive, useMapGenerationJob } from "../../hooks/useMapGenerationJob";
import type { MapGenerationStatusProps } from "./StrategyWorkspace.types";

const ACTIVE_NOTICE = "Generating your map in the background. Keep editing, it will be waiting in Map regions.";
const READY_NOTICE = "Your generated map is ready.";
const FAILED_FALLBACK = "Map generation failed.";

export const MapGenerationStatus: React.FC<MapGenerationStatusProps> = ({
  scenarioId,
  hasSavedMap,
}) => {
  const { data: job } = useMapGenerationJob(scenarioId);
  const regionMapPath = `/studio/${scenarioId}/region-map`;

  if (!job) return null;
  if (isMapJobActive(job)) {
    return (
      <p role="status" className="text-sm text-content-muted">
        {ACTIVE_NOTICE}
      </p>
    );
  }
  if (job.status === "succeeded" && !hasSavedMap) {
    return (
      <p role="status" className="text-sm text-success">
        {READY_NOTICE}{" "}
        <Link className="underline" to={regionMapPath}>
          Open Map regions
        </Link>
      </p>
    );
  }
  if (job.status === "failed") {
    return (
      <p role="alert" className="text-sm text-danger">
        {job.error_message ?? FAILED_FALLBACK}{" "}
        <Link className="underline" to={regionMapPath}>
          Try again
        </Link>
      </p>
    );
  }
  return null;
};
