import { useCallback } from "react";
import { useMutation } from "@tanstack/react-query";
import { toggleBookmarkApi } from "@/shared/api/scenarios.api";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { useToast } from "@/shared/hooks/useToast";

const SAVE_ERROR_MESSAGE = "Couldn't update your saved stories. Try again.";

interface UseSaveScenarioResult {
  isSaved: boolean;
  isPending: boolean;
  handleToggleSave: () => Promise<void>;
}

export const useSaveScenario = (scenarioId: string): UseSaveScenarioResult => {
  const requireAuth = useRequireAuth("save");
  const showToast = useToast();
  const { mutate, data, isPending } = useMutation({
    mutationFn: () => toggleBookmarkApi(scenarioId),
    onError: () => showToast(SAVE_ERROR_MESSAGE, "error"),
  });

  const handleToggleSave = useCallback(async (): Promise<void> => {
    if (await requireAuth()) mutate();
  }, [requireAuth, mutate]);

  return {
    isSaved: data?.is_bookmarked ?? false,
    isPending,
    handleToggleSave,
  };
};
