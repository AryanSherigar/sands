import React from "react";
import type { TerminalChipsProps } from "./TerminalChips.types";

const CHIP_COMMANDS = [
  "anime",
  "song",
  "fact",
  "list",
  "roll",
  "help",
  "clear",
  "home",
] as const;

export const TerminalChips: React.FC<TerminalChipsProps> = ({
  onSelectCommand,
}) => {
  return (
    <div className="flex flex-wrap items-center gap-1.5 border-t border-border-subtle/40 px-4 py-2">
      <span className="font-mono text-[10px] uppercase text-content-faint">
        Quick:
      </span>
      {CHIP_COMMANDS.map((cmd) => (
        <button
          key={cmd}
          type="button"
          onClick={() => onSelectCommand(cmd)}
          className="rounded border border-border-subtle bg-surface-raised px-2 py-0.5 font-mono text-xs text-content-muted transition hover:border-accent/50 hover:bg-surface-overlay hover:text-accent"
        >
          {cmd}
        </button>
      ))}
    </div>
  );
};
