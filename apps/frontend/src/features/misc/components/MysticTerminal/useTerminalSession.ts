import { useState, useRef, useEffect, useCallback } from "react";
import type { TerminalLine } from "../../types/easterEgg.types";
import { getWelcomeLines, processCommand } from "./terminalCommands";

interface UseTerminalSessionOptions {
  onNavigateHome: () => void;
}

export const useTerminalSession = ({
  onNavigateHome,
}: UseTerminalSessionOptions) => {
  const [lines, setLines] = useState<TerminalLine[]>(getWelcomeLines);
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof endRef.current?.scrollIntoView === "function") {
      endRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [lines]);

  const handleExecute = useCallback(
    (rawCommand: string) => {
      const trimmed = rawCommand.trim();
      if (!trimmed) return;

      const userLine: TerminalLine = {
        id: `input-${Date.now()}`,
        type: "input",
        content: trimmed,
      };

      setHistory((prev) => [...prev, trimmed]);
      setHistoryIndex(-1);
      setInput("");

      const result = processCommand(trimmed, onNavigateHome);
      if (result === "CLEAR") {
        setLines([]);
        return;
      }

      setLines((prev) => [...prev, userLine, ...result]);
    },
    [onNavigateHome],
  );

  const handleHistoryNav = useCallback(
    (direction: "up" | "down") => {
      if (history.length === 0) return;

      let nextIndex = historyIndex;
      if (direction === "up") {
        nextIndex =
          historyIndex === -1
            ? history.length - 1
            : Math.max(0, historyIndex - 1);
      } else if (direction === "down") {
        nextIndex = historyIndex === -1 ? -1 : historyIndex + 1;
      }

      setHistoryIndex(nextIndex);
      if (nextIndex >= 0 && nextIndex < history.length) {
        setInput(history[nextIndex]);
      } else {
        setInput("");
      }
    },
    [history, historyIndex],
  );

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLInputElement>) => {
      if (event.key === "Enter") {
        event.preventDefault();
        handleExecute(input);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        handleHistoryNav("up");
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        handleHistoryNav("down");
      }
    },
    [input, handleExecute, handleHistoryNav],
  );

  return {
    lines,
    input,
    setInput,
    endRef,
    handleExecute,
    handleKeyDown,
  };
};
