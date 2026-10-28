import React from "react";
import { Link } from "react-router-dom";
import { Badge } from "@/shared/components/ui/Badge";
import { RangePicker } from "./RangePicker";
import type { ScenarioStatsHeaderProps } from "./ScenarioStatsHeader.types";

const HEADER_LINK = "text-content-muted transition-colors hover:text-content";

export const ScenarioStatsHeader: React.FC<ScenarioStatsHeaderProps> = ({
  scenarioId,
  scenario,
  range,
  onRangeChange,
}) => (
  <header className="flex flex-wrap items-start justify-between gap-4">
    <div className="flex min-w-0 flex-col gap-2">
      <Link
        to="/studio/stats"
        className={`font-mono text-xs uppercase tracking-widest ${HEADER_LINK}`}
      >
        ← Creator stats
      </Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="truncate font-sans text-2xl font-semibold text-content">
          {scenario?.title ?? "Story stats"}
        </h1>
        {scenario && <Badge className="capitalize">{scenario.status}</Badge>}
      </div>
      <div className="flex gap-4 font-sans text-sm">
        <Link to={`/scenario/${scenarioId}`} className={HEADER_LINK}>
          View public page
        </Link>
        <Link to={`/studio/${scenarioId}/edit`} className={HEADER_LINK}>
          Edit
        </Link>
      </div>
    </div>
    <RangePicker value={range} onChange={onRangeChange} />
  </header>
);
