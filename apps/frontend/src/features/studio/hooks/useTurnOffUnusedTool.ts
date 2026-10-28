import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { useToast } from "@/shared/hooks/useToast";
import { logEvent } from "@/shared/lib/logger";
import { SCENARIO_TOOLS, type ToolKey } from "@/shared/constants/scenario-tools";
import { disableToolEnabled } from "../lib/ensureTool";
import { useGuide } from "./useGuide";
import { useToolsInUse } from "./useToolsInUse";

export interface TurnOffUnusedTool {
  shouldOffer: boolean;
  question: string;
  askAfterRemoval: () => void;
  confirm: () => Promise<void>;
  dismiss: () => void;
}

export const useTurnOffUnusedTool = (toolKey: ToolKey): TurnOffUnusedTool => {
  const { scenarioId, scenario } = useGuide();
  const queryClient = useQueryClient();
  const showToast = useToast();
  const { toolsInUse, isReady } = useToolsInUse();
  const [isAsked, setIsAsked] = useState(false);
  const isEnabled = scenario?.enabled_tools?.includes(toolKey) ?? false;
  const displayName = SCENARIO_TOOLS.find((tool) => tool.key === toolKey)?.displayName ?? toolKey;

  const askAfterRemoval = useCallback((): void => setIsAsked(true), []);
  const dismiss = useCallback((): void => setIsAsked(false), []);
  const confirm = useCallback(async (): Promise<void> => {
    if (!scenarioId) return;
    try {
      await disableToolEnabled(queryClient, scenarioId, toolKey);
    } catch (error) {
      logEvent("warning", "tool_turn_off_failed", { toolKey, error: String(error) });
      showToast(`Couldn't turn off ${displayName}. Something still needs it.`, "error");
    }
    setIsAsked(false);
  }, [displayName, queryClient, scenarioId, showToast, toolKey]);

  return {
    shouldOffer: isAsked && isReady && isEnabled && !toolsInUse.has(toolKey),
    question: `Turn off ${displayName} too?`,
    askAfterRemoval,
    confirm,
    dismiss,
  };
};
