import { useLayoutEffect, useState } from "react";
import type { RefObject } from "react";

export const useIsClamped = (
  ref: RefObject<HTMLElement>,
  content: string,
): boolean => {
  const [isClamped, setIsClamped] = useState(false);

  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    setIsClamped(element.scrollHeight > element.clientHeight + 1);
  }, [ref, content]);

  return isClamped;
};
