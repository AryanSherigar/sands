import { useCallback } from "react";
import { useToast } from "@/shared/hooks/useToast";
import { SHARE_COPIED_MESSAGE } from "../constants/scenarioPage.constants";

const COARSE_POINTER_QUERY = "(pointer: coarse)";
const SHARE_FAILED_MESSAGE = "Couldn't share this link";

const canUseNativeShare = (): boolean =>
  typeof navigator.share === "function" &&
  window.matchMedia(COARSE_POINTER_QUERY).matches;

const isUserCancellation = (error: unknown): boolean =>
  error instanceof DOMException && error.name === "AbortError";

export const useShareScenario = (title: string) => {
  const showToast = useToast();

  return useCallback(async (): Promise<void> => {
    const url = `${window.location.origin}${window.location.pathname}`;
    try {
      if (canUseNativeShare()) {
        await navigator.share({ title, url });
        return;
      }
      await navigator.clipboard.writeText(url);
      showToast(SHARE_COPIED_MESSAGE, "success");
    } catch (error) {
      if (isUserCancellation(error)) return;
      showToast(SHARE_FAILED_MESSAGE, "error");
    }
  }, [title, showToast]);
};
