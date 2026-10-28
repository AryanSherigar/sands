import React from "react";
import type { TerminalPromptProps } from "./TerminalPrompt.types";

export const TerminalPrompt: React.FC<TerminalPromptProps> = ({
  input,
  onChange,
  onKeyDown,
}) => {
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.value);
  };

  return (
    <div className="flex items-center gap-2 border-t border-border-subtle/60 px-4 py-2 bg-surface-sunken">
      <span className="font-mono text-xs font-semibold text-accent">{">"}</span>
      <input
        type="text"
        value={input}
        onChange={handleChange}
        onKeyDown={onKeyDown}
        placeholder="Type a rite (e.g. anime, song, roll, help)..."
        aria-label="Terminal prompt"
        autoFocus
        className="w-full bg-transparent font-mono text-xs text-content placeholder:text-content-faint focus:outline-hidden"
      />
    </div>
  );
};
