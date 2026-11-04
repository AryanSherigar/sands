import { useCallback, useEffect, useRef, useState } from "react";
import { logEvent } from "@/shared/lib/logger";

const APPLIED_SUFFIX = ":applied";

const readAppliedKeys = (storageKey: string | null): Set<string> => {
  if (!storageKey) return new Set();
  try {
    const saved = localStorage.getItem(storageKey);
    const parsed: unknown = saved ? JSON.parse(saved) : [];
    return new Set(Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === "string") : []);
  } catch (error) {
    logEvent("warning", "assistant_applied_load_failed", {
      storage_key: storageKey,
      message: error instanceof Error ? error.message : String(error),
    });
    return new Set();
  }
};

export function usePersistedAppliedKeys(chatStorageKey: string | null) {
  const storageKey = chatStorageKey ? `${chatStorageKey}${APPLIED_SUFFIX}` : null;
  const [appliedKeys, setAppliedKeys] = useState<Set<string>>(() => readAppliedKeys(storageKey));
  const previousStorageKeyRef = useRef(storageKey);

  useEffect(() => {
    if (previousStorageKeyRef.current === storageKey) return;
    previousStorageKeyRef.current = storageKey;
    setAppliedKeys(readAppliedKeys(storageKey));
  }, [storageKey]);

  useEffect(() => {
    if (!storageKey || previousStorageKeyRef.current !== storageKey) return;
    try {
      localStorage.setItem(storageKey, JSON.stringify([...appliedKeys]));
    } catch (error) {
      logEvent("warning", "assistant_applied_persist_failed", {
        storage_key: storageKey,
        message: error instanceof Error ? error.message : String(error),
      });
    }
  }, [appliedKeys, storageKey]);

  const markApplied = useCallback((key: string) => {
    setAppliedKeys((previous) => new Set(previous).add(key));
  }, []);

  const resetApplied = useCallback(() => {
    setAppliedKeys(new Set());
    if (storageKey) localStorage.removeItem(storageKey);
  }, [storageKey]);

  return { appliedKeys, markApplied, resetApplied };
}
