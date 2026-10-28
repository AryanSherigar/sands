import { useEffect, useState } from "react";

export const useElementVisibility = (
  element: Element | null,
): boolean => {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    if (!element || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(([entry]) => {
      setIsVisible(entry.isIntersecting);
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [element]);

  return isVisible;
};
