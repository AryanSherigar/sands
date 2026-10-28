import { useEffect, useState } from "react";
import { KEYBOARD_VIEWPORT_RATIO } from "@/shared/constants/navigation";

export const useIsKeyboardOpen = (): boolean => {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const viewport = window.visualViewport;
    if (!viewport) return undefined;
    const handleResize = (): void =>
      setIsOpen(viewport.height < window.innerHeight * KEYBOARD_VIEWPORT_RATIO);
    viewport.addEventListener("resize", handleResize);
    return () => viewport.removeEventListener("resize", handleResize);
  }, []);

  return isOpen;
};
