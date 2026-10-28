import React from "react";
import { SCENARIO_TOOLS } from "@/shared/constants/scenario-tools";
import { ToolRowProps } from "./ToolRow.types";

const nameOf = (toolKey: string): string =>
  SCENARIO_TOOLS.find((tool) => tool.key === toolKey)?.displayName ?? toolKey;

export const ToolRow: React.FC<ToolRowProps> = ({
  tool,
  isEnabled,
  isBusy,
  blockedBy,
  inertCount,
  onToggle,
}) => {
  const isBlocked = isEnabled && blockedBy.length > 0;

  const handleToggle = (): void => {
    onToggle(tool.key, !isEnabled);
  };

  return (
    <li className="flex items-start justify-between gap-4 border border-border-subtle p-4">
      <div className="space-y-1">
        <p className="text-sm font-medium text-content">{tool.displayName}</p>
        <p className="text-xs text-content-faint">{tool.summary}</p>
        {tool.requires.length > 0 && (
          <p className="text-xs text-content-faint">
            Needs {tool.requires.map(nameOf).join(", ")}
          </p>
        )}
        {isBlocked && (
          <p className="text-xs text-content-faint">
            Needed by {blockedBy.map(nameOf).join(", ")}
          </p>
        )}
        {!isEnabled && inertCount > 0 && (
          <p className="text-xs text-warning">
            {inertCount} authored {inertCount === 1 ? "item is" : "items are"}{" "}
            inactive while this tool is off.
          </p>
        )}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={isEnabled}
        aria-label={tool.displayName}
        disabled={isBusy || isBlocked}
        onClick={handleToggle}
        className={`relative h-6 w-11 shrink-0 rounded-full border border-border-subtle transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
          isEnabled ? "bg-accent" : "bg-surface-inset"
        }`}
      >
        <span
          aria-hidden="true"
          className={`absolute top-0.5 h-4 w-4 rounded-full transition-transform ${
            isEnabled
              ? "translate-x-6 bg-surface-inset"
              : "translate-x-1 bg-content-muted"
          }`}
        />
      </button>
    </li>
  );
};
