import { useEffect } from "react";

export const useRuneShortcut = (onToggle: () => void) => {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const is_input =
        target?.tagName === "INPUT" || target?.tagName === "TEXTAREA";
      if (is_input) return;

      if (event.key === "~" || event.key === "`") {
        event.preventDefault();
        onToggle();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onToggle]);
};
