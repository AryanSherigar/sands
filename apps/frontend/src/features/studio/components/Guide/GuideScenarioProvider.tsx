import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useToast } from "@/shared/hooks/useToast";
import { useAddCard, type AddCardOptions } from "../../hooks/useAddCard";
import { useReconcileGuideStep } from "../../hooks/useReconcileGuideStep";
import { useDraftOnFirstWord } from "../../hooks/useDraftOnFirstWord";
import { useScenarioAutosave } from "../../hooks/useScenarioAutosave";
import { useStudioScenario } from "../../hooks/useStudioScenario";
import { disableEditGuard, enableEditGuard, waitForPendingWrites } from "../../lib/editGuard";
import { SAVE_FAILED_MESSAGE } from "../../constants/finish";
import { buildCardTabId } from "../../lib/studioTabs";
import { useStudioStore } from "../../stores/studio.store";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import type { CardKind } from "../../types/card.types";
import type { GuideScenarioProviderProps } from "./Guide.types";
import { GuideContext, type GuideContextValue } from "./guideContext";
import { OtherTypePrompt } from "./OtherTypePrompt";

const ADD_CARD_ERROR_MESSAGE = "Couldn't add the card. Try again.";

export const GuideScenarioProvider: React.FC<GuideScenarioProviderProps> = ({
  scenarioId,
  onDraftCreated,
  children,
}) => {
  const showToast = useToast();
  const { scenario, isLoading } = useStudioScenario(scenarioId);
  const handleCreated = useCallback(
    (created: { scenario_id: string }) => onDraftCreated(created.scenario_id),
    [onDraftCreated],
  );
  const { createDraft } = useDraftOnFirstWord({ onCreated: handleCreated });
  const autosave = useScenarioAutosave(scenarioId, createDraft);
  const [pendingOther, setPendingOther] = useState<AddCardOptions | null>(null);
  useReconcileGuideStep(scenario);

  useEffect(() => {
    if (!scenarioId) return undefined;
    enableEditGuard(scenarioId);
    return () => disableEditGuard(scenarioId);
  }, [scenarioId]);

  useEffect(() => {
    useStudioStore.getState().setHasEditConflict(false);
  }, [scenarioId]);

  const ensureDraft = useCallback(
    async (): Promise<string> => scenarioId ?? (await createDraft({})).scenario_id,
    [createDraft, scenarioId],
  );
  const { flush: flushPendingPatch } = autosave;
  const flushSaves = useCallback(async (): Promise<void> => {
    const isSaved = await flushPendingPatch();
    if (scenarioId) await waitForPendingWrites(scenarioId);
    if (!isSaved) throw new Error(SAVE_FAILED_MESSAGE);
  }, [flushPendingPatch, scenarioId]);
  const createCard = useAddCard(ensureDraft);

  const addCardNow = useCallback(
    async (kind: CardKind, options: AddCardOptions): Promise<void> => {
      try {
        const created = await createCard(kind, options);
        if (options.shouldOpenTab) {
          useStudioTabsStore.getState().openTab(buildCardTabId(created.entity_id));
        }
      } catch {
        showToast(ADD_CARD_ERROR_MESSAGE, "error");
      }
    },
    [createCard, showToast],
  );

  const addCard = useCallback(
    (kind: CardKind, options: AddCardOptions = {}): void => {
      if (kind === "other" && !options.typeName) setPendingOther(options);
      else void addCardNow(kind, options);
    },
    [addCardNow],
  );

  const handleOtherSubmit = (typeName: string): void => {
    const options = pendingOther ?? {};
    setPendingOther(null);
    void addCardNow("other", { ...options, typeName });
  };

  const value = useMemo(
    (): GuideContextValue => ({
      scenarioId,
      scenario,
      isLoading,
      saveFields: autosave.save,
      ensureDraft,
      hasSaveError: autosave.hasError,
      retrySave: autosave.retry,
      flushSaves,
      addCard,
    }),
    [addCard, flushSaves, autosave.hasError, autosave.retry, autosave.save, ensureDraft, isLoading, scenario, scenarioId],
  );

  return (
    <GuideContext.Provider value={value}>
      {children}
      <OtherTypePrompt
        isOpen={pendingOther !== null}
        onSubmit={handleOtherSubmit}
        onClose={() => setPendingOther(null)}
      />
    </GuideContext.Provider>
  );
};
