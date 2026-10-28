import React from "react";
import { getDisplayStatus } from "../../utils/scenarioRowStatus";
import { DraftProgress } from "./DraftProgress";
import { ScenarioRowActions } from "./ScenarioRowActions";
import { ScenarioRowCover } from "./ScenarioRowCover";
import { ScenarioRowMeta } from "./ScenarioRowMeta";
import { ScenarioStatusBadge } from "./ScenarioStatusBadge";
import type { StudioScenarioRowProps } from "./StudioList.types";

const MODE_LABELS = { newbie: "Simple", master: "Advanced", strategy: "Strategy" } as const;

export const StudioScenarioRow: React.FC<StudioScenarioRowProps> = ({
  scenario,
  onDelete,
}) => {
  const status = getDisplayStatus(scenario);
  const isGuideDraft = scenario.mode === "newbie" && status === "draft";
  return (
    <li className="flex flex-col gap-4 rounded-md border border-border-subtle bg-surface-raised p-4 transition-colors hover:bg-surface-overlay md:flex-row md:items-center md:justify-between">
      <div className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-start">
        <ScenarioRowCover scenario={scenario} />
        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="truncate font-display text-xl font-semibold text-content">
              {scenario.title || "Untitled scenario"}
            </h2>
            <span className="rounded-sm bg-surface-inset px-2 py-0.5 font-sans text-xs font-medium text-content-muted">
              {MODE_LABELS[scenario.mode]}
            </span>
            <ScenarioStatusBadge status={status} />
          </div>
          {isGuideDraft && (
            <>
              {scenario.logline && (
                <p className="line-clamp-2 text-meta text-content-muted">{scenario.logline}</p>
              )}
              <DraftProgress scenario={scenario} />
            </>
          )}
          <ScenarioRowMeta scenario={scenario} status={status} />
        </div>
      </div>
      <ScenarioRowActions
        scenario={scenario}
        status={status}
        onDelete={onDelete}
      />
    </li>
  );
};
