import { useEffect, useState } from "react";
import {
  HERO_SCROLL_THRESHOLD_PX,
  SCROLL_CONDENSE_THRESHOLD_PX,
} from "@/shared/constants/navigation";

export interface WindowScrollState {
  isScrolled: boolean;
  isPastHero: boolean;
}

const readScrollState = (): WindowScrollState => ({
  isScrolled: window.scrollY > SCROLL_CONDENSE_THRESHOLD_PX,
  isPastHero: window.scrollY > HERO_SCROLL_THRESHOLD_PX,
});

const isSameState = (a: WindowScrollState, b: WindowScrollState): boolean =>
  a.isScrolled === b.isScrolled && a.isPastHero === b.isPastHero;

export const useWindowScroll = (): WindowScrollState => {
  const [state, setState] = useState<WindowScrollState>(readScrollState);

  useEffect(() => {
    const handleScroll = (): void => {
      const next = readScrollState();
      setState((prev) => (isSameState(prev, next) ? prev : next));
    };
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return state;
};
