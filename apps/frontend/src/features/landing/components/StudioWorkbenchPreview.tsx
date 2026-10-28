import React, { useState } from "react";
import {
  ADVANCED_MODE_CODE,
  SIMPLE_MODE_CODE,
} from "../constants/landing.constants";
import { WorkbenchCodeBlock } from "./WorkbenchCodeBlock";
import type {
  StudioPreviewMode,
  StudioWorkbenchPreviewProps,
} from "./StudioWorkbenchPreview.types";

export const StudioWorkbenchPreview: React.FC<StudioWorkbenchPreviewProps> = ({
  className = "",
}) => {
  const [activeMode, setActiveMode] = useState<StudioPreviewMode>("advanced");
  const isAdvanced = activeMode === "advanced";
  const lines = isAdvanced ? ADVANCED_MODE_CODE : SIMPLE_MODE_CODE;
  const fileName = isAdvanced
    ? "archivist_core.rules.yaml"
    : "hollow_cairn.yaml";

  return (
    <div
      className={`w-full overflow-hidden rounded-md bg-surface-inset p-4 shadow-xs border border-border-subtle ${className}`}
    >
      <div className="mb-3 flex items-center justify-between border-b border-border-subtle pb-3">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-border-strong" />
          <span className="h-2.5 w-2.5 rounded-full bg-border-strong" />
          <span className="h-2.5 w-2.5 rounded-full bg-border-strong" />
          <div className="ml-2 flex items-center gap-2 font-mono text-xs text-content-faint">
            <button
              type="button"
              onClick={() => setActiveMode("simple")}
              className={`rounded px-2 py-0.5 transition-colors ${
                !isAdvanced
                  ? "bg-surface-raised text-primary font-medium"
                  : "hover:text-content"
              }`}
            >
              Simple
            </button>
            <button
              type="button"
              onClick={() => setActiveMode("advanced")}
              className={`rounded px-2 py-0.5 transition-colors ${
                isAdvanced
                  ? "bg-surface-raised text-primary font-medium"
                  : "hover:text-content"
              }`}
            >
              Advanced
            </button>
            <span className="text-content-faint">· {fileName}</span>
          </div>
        </div>
        <span className="rounded border border-[#2B543D] bg-[#162B20] px-2 py-0.5 font-mono text-[11px] font-medium text-[#6BBF8E]">
          SCHEMA VALID
        </span>
      </div>

      <WorkbenchCodeBlock lines={lines} />

      <div className="mt-4 flex items-center justify-between border-t border-border-subtle pt-3 font-mono text-xs text-content-faint">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-success animate-pulse" />
          Deterministic engine idle
        </span>
        <span>latency: 42ms</span>
      </div>
    </div>
  );
};
