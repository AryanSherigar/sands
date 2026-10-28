import React from "react";
import type { TerminalHeaderProps } from "./TerminalHeader.types";

export const TerminalHeader: React.FC<TerminalHeaderProps> = ({ onClose }) => {
  return (
    <div className="flex items-center justify-between border-b border-border-subtle/60 px-4 py-2.5">
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
        <span className="font-mono text-xs font-medium text-accent tracking-wider">
          SANDS VOID TERMINAL v0.4.04
        </span>
      </div>
      <button
        type="button"
        onClick={onClose}
        aria-label="Close terminal"
        className="rounded px-2 py-0.5 font-mono text-xs text-content-faint hover:bg-surface-overlay hover:text-content"
      >
        [Esc]
      </button>
    </div>
  );
};
