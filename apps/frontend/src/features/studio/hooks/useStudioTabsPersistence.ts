import { useEffect, useRef } from "react";
import { logEvent } from "@/shared/lib/logger";
import { STUDIO_TABS_STORAGE_PREFIX } from "../constants/studioTabs";
import { useStudioTabsStore } from "../stores/studioTabs.store";
import type { PersistedStudioTabs } from "../types/studioTab.types";

const isStringArray = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === "string");

const isNullableString = (value: unknown): value is string | null =>
  value === null || typeof value === "string";

const isOptionalBoolean = (value: unknown): boolean =>
  value === undefined || value === null || typeof value === "boolean";

const isPersistedTabs = (value: unknown): value is PersistedStudioTabs => {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    isStringArray(candidate.openTabIds) &&
    isNullableString(candidate.activeTabId) &&
    isNullableString(candidate.splitTabId) &&
    typeof candidate.guideStep === "number" &&
    isOptionalBoolean(candidate.isGuideStepAdvanced)
  );
};

const readSnapshot = (key: string): PersistedStudioTabs | null => {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return null;
    const parsed: unknown = JSON.parse(raw);
    return isPersistedTabs(parsed) ? parsed : null;
  } catch (error) {
    logEvent("warning", "studio_tabs_read_failed", { message: String(error) });
    return null;
  }
};

const writeSnapshot = (key: string, snapshot: PersistedStudioTabs): void => {
  try {
    localStorage.setItem(key, JSON.stringify(snapshot));
  } catch (error) {
    logEvent("warning", "studio_tabs_write_failed", { message: String(error) });
  }
};

const toSnapshot = (state: PersistedStudioTabs): PersistedStudioTabs => ({
  openTabIds: state.openTabIds,
  activeTabId: state.activeTabId,
  splitTabId: state.splitTabId,
  guideStep: state.guideStep,
  isGuideStepAdvanced: state.isGuideStepAdvanced,
});

export const useStudioTabsPersistence = (scenarioId: string | null): void => {
  const wasDraftRef = useRef(false);

  useEffect(() => {
    if (!scenarioId) {
      wasDraftRef.current = true;
      return undefined;
    }
    const key = `${STUDIO_TABS_STORAGE_PREFIX}${scenarioId}`;
    const store = useStudioTabsStore.getState();
    const snapshot = wasDraftRef.current ? null : readSnapshot(key);
    if (wasDraftRef.current) writeSnapshot(key, toSnapshot(store));
    else if (snapshot) store.restoreTabs(snapshot);
    else {
      store.resetTabs();
      store.markResumePending();
    }
    wasDraftRef.current = false;
    return useStudioTabsStore.subscribe((state) =>
      writeSnapshot(key, toSnapshot(state)),
    );
  }, [scenarioId]);
};
