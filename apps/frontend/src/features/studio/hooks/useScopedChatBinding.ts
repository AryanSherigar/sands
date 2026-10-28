import { useCallback, useMemo } from "react";
import { ACTION_TARGET_LABELS, type ActionBlock } from "../types/assistant.types";
import { SLOT_LABELS } from "../constants/scopedChat";
import {
  buildCardTabText,
  buildGuideTabText,
  buildScopedTabLabel,
  clampTabText,
  describeWhereToAccept,
  getSlotForTarget,
  resolveScopedTab,
} from "../lib/scopedChat";
import {
  buildSlotWrite,
  combineText,
  readSlotText,
  type SlotSource,
} from "../lib/scopedSlots";
import { useStudioStore } from "../stores/studio.store";
import { useStudioTabsStore } from "../stores/studioTabs.store";
import type {
  ScopedChatContext,
  ScopedProposal,
  ScopedTab,
  ScopedTabBinding,
  ScopedWriteMode,
} from "../types/scopedChat.types";
import { useEntities } from "./useEntities";
import { useGuide } from "./useGuide";
import { useGuideCards } from "./useGuideCards";
import { useTabLabels } from "./useTabLabels";

const NOTHING_TO_ACCEPT_MESSAGE = "This suggestion does not belong to the open tab.";

const buildTabText = (
  tab: ScopedTab,
  source: SlotSource,
  guideText: string,
): string => {
  if (tab.kind === "guide") return guideText;
  if (tab.kind === "card") return buildCardTabText(source.entity);
  return "";
};

export const useScopedChatBinding = (): ScopedTabBinding => {
  const { scenarioId, scenario, saveFields } = useGuide();
  const { entities, cards } = useGuideCards();
  const { updateEntityAsync } = useEntities(scenarioId);
  const getTabLabel = useTabLabels();
  const activeTabId = useStudioTabsStore((state) => state.activeTabId);
  const guideStep = useStudioTabsStore((state) => state.guideStep);
  const guideView = useStudioTabsStore((state) => state.guideView);
  const isAdvanced = scenario?.mode === "master";
  const tab = useMemo(
    () => resolveScopedTab(activeTabId, guideStep, guideView, isAdvanced),
    [activeTabId, guideStep, guideView, isAdvanced],
  );
  const entity = useMemo(() => {
    if (tab.kind !== "card") return null;
    return entities.find((candidate) => candidate.entity_id === tab.entityId) ?? null;
  }, [entities, tab]);
  const source = useMemo((): SlotSource => ({ scenario, entity }), [scenario, entity]);

  const context = useMemo((): ScopedChatContext => {
    const guideText = tab.kind === "guide" ? buildGuideTabText(tab.stepId, scenario, cards) : "";
    return {
      oneLineIdea: scenario?.logline ?? "",
      tabKind: tab.kind,
      tabLabel: activeTabId ? buildScopedTabLabel(tab, getTabLabel(activeTabId)) : "",
      tabText: clampTabText(buildTabText(tab, source, guideText)),
    };
  }, [activeTabId, cards, getTabLabel, scenario, source, tab]);

  const describeProposal = useCallback(
    (block: ActionBlock): ScopedProposal => {
      const slot = getSlotForTarget(tab, block.target);
      if (!slot) {
        return {
          label: ACTION_TARGET_LABELS[block.target] ?? block.target,
          before: "",
          after: block.content,
          canApply: false,
          reason: `Open ${describeWhereToAccept(block.target)} to accept this.`,
        };
      }
      const label = slot === "card_lore" && entity ? entity.canonical_name : SLOT_LABELS[slot];
      return { label, before: readSlotText(slot, source), after: block.content, canApply: true, reason: null };
    },
    [entity, source, tab],
  );

  const applyProposal = useCallback(
    async (block: ActionBlock, mode: ScopedWriteMode): Promise<void> => {
      const slot = getSlotForTarget(tab, block.target);
      if (!slot) throw new Error(NOTHING_TO_ACCEPT_MESSAGE);
      const text = combineText(readSlotText(slot, source), block.content.trim(), mode);
      const write = buildSlotWrite(slot, source, text);
      if (write.scenarioPatch) saveFields(write.scenarioPatch);
      if (!write.entityUpdate || !entity) return;
      const { setSaveState } = useStudioStore.getState();
      setSaveState(true);
      try {
        await updateEntityAsync({ entityId: entity.entity_id, payload: write.entityUpdate });
        setSaveState(false, new Date());
      } catch (error) {
        setSaveState(false);
        throw error;
      }
    },
    [entity, saveFields, source, tab, updateEntityAsync],
  );

  return useMemo(
    () => ({ context, describeProposal, applyProposal }),
    [applyProposal, context, describeProposal],
  );
};
