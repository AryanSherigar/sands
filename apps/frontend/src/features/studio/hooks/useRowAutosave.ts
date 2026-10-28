import { useCallback, useEffect, useRef } from "react";
import { ROW_AUTOSAVE_DEBOUNCE_MS } from "../constants/advancedCards";
import { useSyncedValue } from "./useSyncedValue";

interface UseRowAutosaveParams<Draft> {
  serverDraft: Draft;
  save: (draft: Draft) => void;
}

interface RowAutosave<Draft> {
  value: Draft;
  commit: (next: Draft) => void;
  flush: () => void;
}

export const useRowAutosave = <Draft,>({ serverDraft, save }: UseRowAutosaveParams<Draft>): RowAutosave<Draft> => {
  const saveRef = useRef(save);
  const pendingRef = useRef<{ draft: Draft } | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    saveRef.current = save;
  });

  const clearTimer = useCallback((): void => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = null;
  }, []);

  const flush = useCallback((): void => {
    clearTimer();
    const pending = pendingRef.current;
    if (!pending) return;
    pendingRef.current = null;
    saveRef.current(pending.draft);
  }, [clearTimer]);

  const arm = useCallback((): void => {
    clearTimer();
    timerRef.current = setTimeout(flush, ROW_AUTOSAVE_DEBOUNCE_MS);
  }, [clearTimer, flush]);

  const schedule = useCallback(
    (draft: Draft): void => {
      pendingRef.current = { draft };
      arm();
    },
    [arm],
  );

  useEffect(() => flush, [flush]);

  const synced = useSyncedValue(serverDraft, schedule);
  return { ...synced, flush };
};
