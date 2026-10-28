import { useCallback, useEffect, useRef, useState } from "react";
import { logEvent } from "@/shared/lib/logger";
import { CARD_AUTOSAVE_DEBOUNCE_MS } from "../constants/card";
import { useStudioStore } from "../stores/studio.store";
import type { CardDraft } from "../lib/cardDraft";

export const useCardAutosave = (save: (draft: CardDraft) => Promise<unknown>) => {
  const setSaveState = useStudioStore((state) => state.setSaveState);
  const [hasError, setHasError] = useState(false);
  const pendingDraftRef = useRef<CardDraft | null>(null);
  const failedDraftRef = useRef<CardDraft | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const saveRef = useRef(save);

  useEffect(() => {
    saveRef.current = save;
  }, [save]);

  const clearTimer = useCallback((): void => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = null;
  }, []);

  const flush = useCallback(async (): Promise<void> => {
    const draft = pendingDraftRef.current;
    if (!draft) return;
    pendingDraftRef.current = null;
    clearTimer();
    setSaveState(true);
    try {
      await saveRef.current(draft);
      failedDraftRef.current = null;
      setHasError(false);
      setSaveState(false, new Date());
    } catch (error) {
      failedDraftRef.current = draft;
      setHasError(true);
      setSaveState(false);
      logEvent("warning", "card_autosave_failed", { error: String(error) });
    }
  }, [clearTimer, setSaveState]);

  const schedule = useCallback(
    (draft: CardDraft): void => {
      pendingDraftRef.current = draft;
      clearTimer();
      timerRef.current = setTimeout(() => void flush(), CARD_AUTOSAVE_DEBOUNCE_MS);
    },
    [clearTimer, flush],
  );

  const retry = useCallback((): void => {
    pendingDraftRef.current = pendingDraftRef.current ?? failedDraftRef.current;
    void flush();
  }, [flush]);

  useEffect(() => () => void flush(), [flush]);

  return { schedule, retry, hasError };
};
