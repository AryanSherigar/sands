import React, { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import type { MysticTerminalProps } from "./MysticTerminal.types";
import { TerminalHeader } from "./TerminalHeader";
import { TerminalChips } from "./TerminalChips";
import { TerminalLineItem } from "./TerminalLineItem";
import { TerminalPrompt } from "./TerminalPrompt";
import { useTerminalSession } from "./useTerminalSession";
import { useEscapeKey } from "./useEscapeKey";

export const MysticTerminal: React.FC<MysticTerminalProps> = ({
  is_open,
  onClose,
}) => {
  const navigate = useNavigate();
  const handleNavigateHome = useCallback(() => navigate("/"), [navigate]);
  const session = useTerminalSession({ onNavigateHome: handleNavigateHome });
  useEscapeKey(is_open, onClose);

  if (!is_open) return null;

  return (
    <div className="w-full max-w-xl overflow-hidden rounded-xl border border-accent/40 bg-surface-sunken/95 shadow-accent-glow backdrop-blur-sm">
      <TerminalHeader onClose={onClose} />
      <div className="flex max-h-72 flex-col gap-2.5 overflow-y-auto p-4">
        {session.lines.map((line) => (
          <TerminalLineItem key={line.id} line={line} />
        ))}
        <div ref={session.endRef} />
      </div>
      <TerminalChips onSelectCommand={session.handleExecute} />
      <TerminalPrompt
        input={session.input}
        onChange={session.setInput}
        onKeyDown={session.handleKeyDown}
      />
    </div>
  );
};
