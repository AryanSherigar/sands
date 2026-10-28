import { useEffect, useRef } from "react";
import { LOAD_MORE_ROOT_MARGIN } from "@/shared/constants/scroll";

export const useLoadMoreTrigger = (
  onReachEnd: () => void,
  isEnabled: boolean,
): React.RefObject<HTMLDivElement> => {
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!isEnabled || !sentinel || typeof IntersectionObserver === "undefined") {
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) onReachEnd();
      },
      { rootMargin: LOAD_MORE_ROOT_MARGIN },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [isEnabled, onReachEnd]);

  return sentinelRef;
};
