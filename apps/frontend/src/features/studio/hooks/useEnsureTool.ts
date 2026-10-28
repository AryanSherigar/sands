import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import type { ToolKey } from "@/shared/constants/scenario-tools";
import { ensureToolEnabled } from "../lib/ensureTool";
import { useGuide } from "./useGuide";

export interface EnsureTool {
  ensureTool: (toolKey: ToolKey) => Promise<void>;
}

export const useEnsureTool = (): EnsureTool => {
  const { ensureDraft } = useGuide();
  const queryClient = useQueryClient();

  const ensureTool = useCallback(
    async (toolKey: ToolKey): Promise<void> => {
      const scenarioId = await ensureDraft();
      await ensureToolEnabled(queryClient, scenarioId, toolKey);
    },
    [ensureDraft, queryClient],
  );

  return { ensureTool };
};
