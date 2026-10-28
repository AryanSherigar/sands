import React from "react";
import type { WorkbenchCodeBlockProps } from "./WorkbenchCodeBlock.types";

export const WorkbenchCodeBlock: React.FC<WorkbenchCodeBlockProps> = ({
  lines,
}) => {
  return (
    <div className="space-y-1 overflow-x-auto font-mono text-xs leading-loose text-content-muted">
      {lines.map(({ line, indent = "", key, val, isDanger }) => (
        <div key={`${line}-${key}`} className="flex gap-2">
          <span className="select-none text-content-faint">{line}</span>
          <span className="text-content whitespace-pre">{indent}</span>
          <span className="text-accent">{key}</span>
          {val && (
            <span className={isDanger ? "text-[#E8716A] font-medium" : "text-content"}>
              {val}
            </span>
          )}
        </div>
      ))}
    </div>
  );
};
