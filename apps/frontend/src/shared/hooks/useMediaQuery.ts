import { useEffect, useState } from "react";

const readMatch = (query: string): boolean =>
  typeof window.matchMedia === "function" && window.matchMedia(query).matches;

export const useMediaQuery = (query: string): boolean => {
  const [isMatch, setIsMatch] = useState<boolean>(() => readMatch(query));

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return undefined;
    const list = window.matchMedia(query);
    const handleChange = (): void => setIsMatch(list.matches);
    handleChange();
    list.addEventListener("change", handleChange);
    return () => list.removeEventListener("change", handleChange);
  }, [query]);

  return isMatch;
};
