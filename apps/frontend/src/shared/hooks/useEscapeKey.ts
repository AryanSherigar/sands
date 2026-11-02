import { useEffect } from "react";

export const useEscapeKey = (isActive: boolean, onEscape: () => void): void => {
  useEffect(() => {
    if (!isActive) return undefined;
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") onEscape();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isActive, onEscape]);
};
