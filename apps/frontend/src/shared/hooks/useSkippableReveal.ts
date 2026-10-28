import { useEffect, useState } from "react";

interface SkippableReveal {
  isSkipped: boolean;
  skip: () => void;
}

export function useSkippableReveal(): SkippableReveal {
  const [isSkipped, setIsSkipped] = useState(false);

  useEffect(() => {
    if (isSkipped) return undefined;
    const handleSkip = () => setIsSkipped(true);
    window.addEventListener("keydown", handleSkip);
    window.addEventListener("pointerdown", handleSkip);
    return () => {
      window.removeEventListener("keydown", handleSkip);
      window.removeEventListener("pointerdown", handleSkip);
    };
  }, [isSkipped]);

  return { isSkipped, skip: () => setIsSkipped(true) };
}
