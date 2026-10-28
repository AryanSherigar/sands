import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { useToast } from "@/shared/hooks/useToast";
import { logEvent } from "@/shared/lib/logger";
import {
  EXTRAS,
  EXTRA_SWITCH_FAILED_MESSAGE,
  type ExtraDefinition,
  type ExtraId,
  type ExtraRemoval,
} from "../constants/extras";
import { ADVANCED_MODE_ON } from "../constants/advancedMode";
import { disableToolEnabled } from "../lib/ensureTool";
import { buildExtraRemoval, buildExtraTabId, hasToolUseOutsideExtra, isExtraOn } from "../lib/extras";
import { useStudioTabsStore } from "../stores/studioTabs.store";
import { useEnsureTool } from "./useEnsureTool";
import { useGuide } from "./useGuide";
import { useMaps } from "./useMaps";
import { useScenarioMusic } from "./useScenarioMusic";
import { useToolsInUse } from "./useToolsInUse";

interface ExtraView {
  extra: ExtraDefinition;
  isOn: boolean;
  removal: ExtraRemoval | null;
}

interface ExtrasApi {
  views: ExtraView[];
  add: (extra: ExtraDefinition) => Promise<void>;
  open: (extra: ExtraDefinition) => void;
  remove: (extra: ExtraDefinition) => Promise<void>;
}

export const useExtras = (): ExtrasApi => {
  const { scenarioId, scenario } = useGuide();
  const queryClient = useQueryClient();
  const { ensureTool } = useEnsureTool();
  const openTab = useStudioTabsStore((state) => state.openTab);
  const closeTab = useStudioTabsStore((state) => state.closeTab);
  const showToast = useToast();
  const { maps } = useMaps(scenarioId);
  const { slots } = useScenarioMusic(scenarioId);
  const { usage, isReady } = useToolsInUse();
  const isAdvanced = scenario?.mode === ADVANCED_MODE_ON;
  const enabledTools = scenario?.enabled_tools ?? [];
  const hasContentById: Partial<Record<ExtraId, boolean>> = {
    map: maps.length > 0,
    music: slots.length > 0,
    minigames: usage.minigames.length > 0,
  };

  const views: ExtraView[] = EXTRAS.map((extra) => ({
    extra,
    isOn: isExtraOn(extra, {
      isAdvanced,
      enabledTools,
      hasContent: hasContentById[extra.id] ?? false,
    }),
    removal: buildExtraRemoval(extra, usage, isReady),
  }));

  const open = useCallback(
    (extra: ExtraDefinition): void => openTab(buildExtraTabId(extra.id)),
    [openTab],
  );

  const add = useCallback(
    async (extra: ExtraDefinition): Promise<void> => {
      try {
        if (extra.tool) await ensureTool(extra.tool);
      } catch (error) {
        logEvent("warning", "extra_enable_failed", { extra: extra.id, error: String(error) });
        showToast(EXTRA_SWITCH_FAILED_MESSAGE, "error");
        return;
      }
      open(extra);
    },
    [ensureTool, open, showToast],
  );

  const remove = useCallback(
    async (extra: ExtraDefinition): Promise<void> => {
      if (!extra.tool || !scenarioId || !isReady || hasToolUseOutsideExtra(extra, usage)) return;
      try {
        await disableToolEnabled(queryClient, scenarioId, extra.tool);
        closeTab(buildExtraTabId(extra.id));
      } catch (error) {
        logEvent("warning", "extra_disable_failed", { extra: extra.id, error: String(error) });
        showToast(EXTRA_SWITCH_FAILED_MESSAGE, "error");
      }
    },
    [closeTab, isReady, queryClient, scenarioId, showToast, usage],
  );

  return { views, add, open, remove };
};
