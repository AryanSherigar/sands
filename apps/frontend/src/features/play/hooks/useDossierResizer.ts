import { useCallback, useEffect, useState } from "react";

export const MIN_DOSSIER_WIDTH = 340;
export const MAX_DOSSIER_WIDTH = 640;
export const DEFAULT_DOSSIER_WIDTH = 400;

export function useDossierResizer() {
  const [width, setWidth] = useState(DEFAULT_DOSSIER_WIDTH);
  const [isDragging, setIsDragging] = useState(false);

  const startDrag = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "ArrowLeft") {
      setWidth((w) => Math.min(MAX_DOSSIER_WIDTH, w + 20));
    } else if (e.key === "ArrowRight") {
      setWidth((w) => Math.max(MIN_DOSSIER_WIDTH, w - 20));
    }
  }, []);

  useEffect(() => {
    if (!isDragging) return;

    const onPointerMove = (clientX: number) => {
      const maxAllowed = Math.min(MAX_DOSSIER_WIDTH, window.innerWidth - 420);
      const newWidth = Math.min(maxAllowed, Math.max(MIN_DOSSIER_WIDTH, window.innerWidth - clientX));
      setWidth(newWidth);
    };

    const onMouseMove = (e: MouseEvent) => onPointerMove(e.clientX);
    const onTouchMove = (e: TouchEvent) => {
      if (e.touches[0]) onPointerMove(e.touches[0].clientX);
    };
    const onStop = () => setIsDragging(false);

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onStop);
    window.addEventListener("touchmove", onTouchMove);
    window.addEventListener("touchend", onStop);

    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onStop);
      window.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("touchend", onStop);
    };
  }, [isDragging]);

  return {
    width,
    isDragging,
    minWidth: MIN_DOSSIER_WIDTH,
    maxWidth: MAX_DOSSIER_WIDTH,
    startDrag,
    handleKeyDown,
  };
}
