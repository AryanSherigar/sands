import { useEffect, useState } from "react";

// Reports true once the tab has stayed hidden for longer than `graceMs` while
// `isActive`, and stays true until `isActive` turns false. A quick glance away
// (shorter than the grace) is forgiven. The server decides whether it matters.
export const usePageHiddenGrace = (
  isActive: boolean,
  graceMs: number,
): boolean => {
  const [wasHidden, setWasHidden] = useState(false);

  useEffect(() => {
    if (!isActive) {
      setWasHidden(false);
      return;
    }
    let graceTimer: number | null = null;
    const clearGrace = (): void => {
      if (graceTimer === null) return;
      window.clearTimeout(graceTimer);
      graceTimer = null;
    };
    const handleVisibilityChange = (): void => {
      if (!document.hidden) {
        clearGrace();
        return;
      }
      clearGrace();
      graceTimer = window.setTimeout(() => setWasHidden(true), graceMs);
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    if (document.hidden) handleVisibilityChange();
    return () => {
      clearGrace();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [isActive, graceMs]);

  return wasHidden;
};
