import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { PAGE_SCROLL_ATTRIBUTE } from "@/shared/constants/scroll";

const COMPACT_ENTER_SCROLL_Y = 96;
const COMPACT_EXIT_SCROLL_Y = 16;

export const usePageScrollCompact = (): boolean => {
  const { pathname } = useLocation();
  const [isCompact, setIsCompact] = useState(false);
  const scrollTopRef = useRef(0);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    setIsCompact(false);
  }, [pathname]);

  useEffect(() => {
    const applyCompactState = (): void => {
      frameRef.current = null;
      const top = scrollTopRef.current;
      setIsCompact((prev) =>
        prev ? top > COMPACT_EXIT_SCROLL_Y : top > COMPACT_ENTER_SCROLL_Y,
      );
    };

    // NOTE: identity check via hasAttribute, not closest() — closest() would
    // also match nested overflow-y-auto boxes (e.g. a modal) inside the page
    // and reintroduce cross-container scroll noise.
    const handleScroll = (event: Event): void => {
      const target = event.target;
      if (
        !(target instanceof HTMLElement) ||
        !target.hasAttribute(PAGE_SCROLL_ATTRIBUTE)
      ) {
        return;
      }
      scrollTopRef.current = target.scrollTop;
      if (frameRef.current === null) {
        frameRef.current = requestAnimationFrame(applyCompactState);
      }
    };

    window.addEventListener("scroll", handleScroll, true);
    return () => {
      window.removeEventListener("scroll", handleScroll, true);
      if (frameRef.current !== null) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, []);

  return isCompact;
};
