import { useCallback, useState } from "react";
import type { CopyState } from "../types/statsView.types";

export const useCopyToClipboard = () => {
  const [copyState, setCopyState] = useState<CopyState>("idle");

  const copyText = useCallback(async (text: string): Promise<void> => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
  }, []);

  return { copyState, copyText };
};
