import React, { useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { NotFoundMessage } from "../components/NotFoundMessage/NotFoundMessage";
import { RuneGlyph } from "../components/RuneGlyph/RuneGlyph";
import { MysticTerminal } from "../components/MysticTerminal/MysticTerminal";
import { useRuneShortcut } from "../hooks/useRuneShortcut";

export const NotFoundPage: React.FC = () => {
  const [is_terminal_open, setIsTerminalOpen] = useState(false);

  const handleToggleTerminal = useCallback(() => {
    setIsTerminalOpen((prev) => !prev);
  }, []);

  const handleCloseTerminal = useCallback(() => {
    setIsTerminalOpen(false);
  }, []);

  useRuneShortcut(handleToggleTerminal);

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-5 bg-surface px-6 py-12 text-center">
      <NotFoundMessage />
      <Link
        to="/"
        className="rounded-md border border-border-subtle bg-surface-raised px-4 py-2 font-sans text-sm text-content-muted transition hover:bg-surface-overlay hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
      >
        Back to sands
      </Link>
      <RuneGlyph
        onActivate={handleToggleTerminal}
        is_active={is_terminal_open}
      />
      <MysticTerminal
        is_open={is_terminal_open}
        onClose={handleCloseTerminal}
      />
    </main>
  );
};
