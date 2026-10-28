import { useEffect, useRef, useState } from "react";
import { useToast } from "@/shared/hooks/useToast";
import { PLAYTEST_NO_OPENING_MESSAGE } from "../constants/playtest";
import { PLAYTEST_TAB_ID } from "../constants/studioTabs";
import { hasOpeningText } from "../lib/finishChecklist";
import { buildInitialSetupValues, needsSetupForm } from "../lib/playtestSetup";
import { usePlaytestStore } from "../stores/playtest.store";
import { useStudioTabsStore } from "../stores/studioTabs.store";
import { useGuide } from "./useGuide";
import { usePlaytestSession } from "./usePlaytestSession";

export const usePlaytestTab = (cancelTurn: () => void) => {
  const { scenarioId, scenario } = useGuide();
  const sessionScenarioId = usePlaytestStore((state) => state.scenarioId);
  const playthroughId = usePlaytestStore((state) => state.playthroughId);
  const startedStamp = usePlaytestStore((state) => state.startedStamp);
  const setupValues = usePlaytestStore((state) => state.setupValues);
  const endSession = usePlaytestStore((state) => state.endSession);
  const pendingTest = usePlaytestStore((state) => state.pendingTest);
  const clearPendingTest = usePlaytestStore((state) => state.clearPendingTest);
  const closeTab = useStudioTabsStore((state) => state.closeTab);
  const session = usePlaytestSession();
  const showToast = useToast();
  const [dismissedStamp, setDismissedStamp] = useState<string | null>(null);
  const hasAutoStartedRef = useRef(false);

  const setupFields = scenario?.setup_schema ?? [];
  const hasSession = playthroughId !== null && sessionScenarioId === scenarioId;
  const hasOpening = hasOpeningText(scenario);
  const needsForm = needsSetupForm(setupFields);
  const currentStamp = scenario?.content_edited_at ?? null;
  const isStale =
    hasSession && Boolean(startedStamp) && currentStamp !== startedStamp && currentStamp !== dismissedStamp;

  useEffect(() => {
    if (!pendingTest || session.isStarting) return;
    clearPendingTest();
    if (!hasOpening) showToast(PLAYTEST_NO_OPENING_MESSAGE, "info");
    if (!hasOpening || !scenarioId) return;
    cancelTurn();
    hasAutoStartedRef.current = true;
    const values = hasSession ? setupValues : buildInitialSetupValues(setupFields);
    void session.start(values, pendingTest);
  });

  useEffect(() => {
    const canAutoStart = !hasSession && hasOpening && !needsForm && Boolean(scenarioId);
    if (!canAutoStart || hasAutoStartedRef.current) return;
    hasAutoStartedRef.current = true;
    void session.start(buildInitialSetupValues(setupFields));
  });

  const restart = (): void => {
    cancelTurn();
    setDismissedStamp(null);
    void session.start(hasSession ? setupValues : buildInitialSetupValues(setupFields));
  };
  const end = (): void => {
    cancelTurn();
    endSession();
    closeTab(PLAYTEST_TAB_ID);
  };

  return {
    hasSession,
    hasOpening,
    needsForm,
    setupFields,
    isStale,
    isStarting: session.isStarting,
    startError: session.startError,
    start: session.start,
    retryStart: () => void session.start(hasSession ? setupValues : buildInitialSetupValues(setupFields)),
    restart,
    end,
    keepPlaying: () => setDismissedStamp(currentStamp),
  };
};
