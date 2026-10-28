import React from "react";
import {
  getComplexityLabel,
  getModeLabel,
} from "../../../utils/scenarioPage.utils";
import type { QuickSpecsProps } from "./QuickSpecs.types";

export const QuickSpecs: React.FC<QuickSpecsProps> = ({
  estimatedPlaytime,
  mode,
  complexityTier,
}) => (
  <dl className="space-y-2 rounded-md border border-border-subtle bg-surface-raised p-5 font-mono text-xs">
    {estimatedPlaytime && (
      <div className="flex items-center justify-between gap-3">
        <dt className="text-content-faint">Typical run</dt>
        <dd className="text-content">{estimatedPlaytime}</dd>
      </div>
    )}
    <div className="flex items-center justify-between gap-3">
      <dt className="text-content-faint">Mode</dt>
      <dd className="text-content">
        {getModeLabel(mode)} · {getComplexityLabel(complexityTier)}
      </dd>
    </div>
  </dl>
);
