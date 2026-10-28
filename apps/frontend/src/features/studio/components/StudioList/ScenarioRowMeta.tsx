import React from "react";
import { formatRelativeTime } from "@/shared/lib/formatRelativeTime";
import { isLiveStatus } from "../../utils/scenarioRowStatus";
import { ScenarioFailedPublishNote } from "./ScenarioFailedPublishNote";
import { ScenarioPublishedMetrics } from "./ScenarioPublishedMetrics";
import type { ScenarioRowMetaProps } from "./StudioList.types";

export const ScenarioRowMeta: React.FC<ScenarioRowMetaProps> = ({
  scenario,
  status,
}) => (
  <div className="flex flex-col gap-1">
    <p className="font-mono text-xs text-content-faint">
      Edited {formatRelativeTime(scenario.content_edited_at, new Date())}
    </p>
    {isLiveStatus(status) && <ScenarioPublishedMetrics scenario={scenario} />}
    {status === "publish_failed" && (
      <ScenarioFailedPublishNote scenario={scenario} />
    )}
  </div>
);
