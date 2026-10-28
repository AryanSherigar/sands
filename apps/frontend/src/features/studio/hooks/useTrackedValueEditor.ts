import { useCallback, useEffect, useMemo, useRef } from "react";
import { useToast } from "@/shared/hooks/useToast";
import { logEvent } from "@/shared/lib/logger";
import { HUD_ENABLE_FAILED_MESSAGE } from "../constants/trackedValues";
import { buildStateField, buildValueKey } from "../lib/trackedValueSchema";
import { usesStatusHud } from "../lib/trackedValueEditing";
import type { StateFieldDefinition } from "../types/scenario.types";
import type { NewTrackedValue } from "../types/trackedValue.types";
import { useEnsureTool } from "./useEnsureTool";
import { useGuide } from "./useGuide";
import { useSyncedValue } from "./useSyncedValue";
import { useTurnOffUnusedTool, type TurnOffUnusedTool } from "./useTurnOffUnusedTool";

type Schema = Record<string, StateFieldDefinition>;
const HUD_TOOL_KEY = "status_hud";
const NO_SCHEMA: Schema = {};

interface TrackedValueEditor {
  schema: Schema;
  entries: Array<[string, StateFieldDefinition]>;
  hudTool: TurnOffUnusedTool;
  writeField: (key: string, next: StateFieldDefinition) => Promise<void>;
  addValue: (input: NewTrackedValue) => Promise<string | null>;
  removeValue: (key: string) => void;
}

export const useTrackedValueEditor = (): TrackedValueEditor => {
  const { scenario, saveFields } = useGuide();
  const { ensureTool } = useEnsureTool();
  const showToast = useToast();
  const hudTool = useTurnOffUnusedTool(HUD_TOOL_KEY);
  const serverSchema = scenario?.state_schema ?? NO_SCHEMA;
  const { value: schema, commit } = useSyncedValue<Schema>(serverSchema, (next) =>
    saveFields({ state_schema: next }),
  );
  const schemaRef = useRef(schema);
  useEffect(() => {
    schemaRef.current = schema;
  });

  const ensureHud = useCallback(async (): Promise<boolean> => {
    try {
      await ensureTool(HUD_TOOL_KEY);
      return true;
    } catch (error) {
      logEvent("warning", "status_hud_enable_failed", { error: String(error) });
      showToast(HUD_ENABLE_FAILED_MESSAGE, "error");
      return false;
    }
  }, [ensureTool, showToast]);

  const writeField = useCallback(
    async (key: string, next: StateFieldDefinition): Promise<void> => {
      const previous = schemaRef.current[key];
      const wasShown = previous !== undefined && usesStatusHud(previous);
      const isShown = usesStatusHud(next);
      if (isShown && !(await ensureHud())) return;
      commit({ ...schemaRef.current, [key]: next });
      if (wasShown && !isShown) hudTool.askAfterRemoval();
    },
    [commit, ensureHud, hudTool],
  );

  const addValue = useCallback(
    async (input: NewTrackedValue): Promise<string | null> => {
      const key = buildValueKey(input.name, new Set(Object.keys(schemaRef.current)));
      const field = buildStateField(input);
      if (usesStatusHud(field) && !(await ensureHud())) return null;
      commit({ ...schemaRef.current, [key]: field });
      return key;
    },
    [commit, ensureHud],
  );

  const removeValue = useCallback(
    (key: string): void => {
      const { [key]: removed, ...rest } = schemaRef.current;
      commit(rest);
      if (removed && usesStatusHud(removed)) hudTool.askAfterRemoval();
    },
    [commit, hudTool],
  );

  const entries = useMemo(() => Object.entries(schema), [schema]);

  return { schema, entries, hudTool, writeField, addValue, removeValue };
};
