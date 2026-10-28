import React from "react";
import {
  SCENARIO_TOOLS,
  getEnabledDependents,
} from "@/shared/constants/scenario-tools";
import { useScenarioTools } from "../../hooks/useScenarioTools";
import { ToolRow } from "./ToolRow";
import { ToolsTabProps } from "./ToolsTab.types";

const nameOf = (toolKey: string): string =>
  SCENARIO_TOOLS.find((tool) => tool.key === toolKey)?.displayName ?? toolKey;

export const ToolsTab: React.FC<ToolsTabProps> = ({ scenarioId }) => {
  const { tools, isLoading, updateTools, isUpdating, lastAutoEnabled, updateError } =
    useScenarioTools(scenarioId);

  if (isLoading || !tools) {
    return <p className="text-sm text-content-faint">Loading tools...</p>;
  }

  const handleToggle = (toolKey: string, shouldEnable: boolean): void => {
    const next = shouldEnable
      ? [...tools.enabled_tools, toolKey]
      : tools.enabled_tools.filter((key) => key !== toolKey);
    updateTools({ enabled_tools: next });
  };

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-content">Tools</h2>
      <p className="text-xs text-content-faint">
        Switch on only what this story needs. A story with no tools plays exactly
        as before.
      </p>
      {updateError && <p className="text-xs text-danger">{updateError}</p>}
      {lastAutoEnabled.length > 0 && (
        <p role="status" className="text-xs text-content-muted">
          {lastAutoEnabled.map(nameOf).join(", ")} was also switched on because
          another tool needs it.
        </p>
      )}
      <ul className="space-y-3">
        {SCENARIO_TOOLS.map((tool) => (
          <ToolRow
            key={tool.key}
            tool={tool}
            isEnabled={tools.enabled_tools.includes(tool.key)}
            isBusy={isUpdating}
            blockedBy={getEnabledDependents(tool.key, tools.enabled_tools)}
            inertCount={tools.inert_data[tool.key] ?? 0}
            onToggle={handleToggle}
          />
        ))}
      </ul>
    </div>
  );
};
