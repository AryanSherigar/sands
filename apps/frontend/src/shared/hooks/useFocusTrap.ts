import { useEffect, type RefObject } from "react";

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

const getFocusableElements = (container: HTMLElement): HTMLElement[] =>
  Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));

const wrapTabFocus = (event: KeyboardEvent, container: HTMLElement): void => {
  const focusable = getFocusableElements(container);
  if (focusable.length === 0) {
    event.preventDefault();
    return;
  }
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  const isLeavingStart = event.shiftKey && document.activeElement === first;
  const isLeavingEnd = !event.shiftKey && document.activeElement === last;
  if (isLeavingStart || isLeavingEnd) {
    event.preventDefault();
    (isLeavingStart ? last : first).focus();
  }
};

export const useFocusTrap = (
  containerRef: RefObject<HTMLElement>,
  isActive: boolean,
): void => {
  useEffect(() => {
    const container = containerRef.current;
    if (!isActive || !container) return undefined;

    const previouslyFocused = document.activeElement as HTMLElement | null;
    (getFocusableElements(container)[0] ?? container).focus();

    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Tab") wrapTabFocus(event, container);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previouslyFocused?.focus();
    };
  }, [containerRef, isActive]);
};
