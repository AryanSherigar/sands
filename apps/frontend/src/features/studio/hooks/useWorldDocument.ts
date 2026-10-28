import { useMemo } from "react";
import { useGuide } from "./useGuide";
import { useServerSyncedState } from "./useServerSyncedState";
import { readWorldDocument } from "../lib/worldDocuments";
import type { LoreDocument } from "../types/lore.types";

export const useWorldDocument = (key: string) => {
  const { scenario, saveFields } = useGuide();
  const stored = scenario?.world_data?.[key];
  const serverDocument = useMemo(
    () => readWorldDocument({ [key]: stored }, key),
    [key, stored],
  );
  const [local, setLocal] = useServerSyncedState<LoreDocument>(serverDocument);

  const onChange = (next: LoreDocument): void => {
    setLocal(next);
    saveFields({ worldData: { [key]: next } });
  };

  return { document: local ?? serverDocument, onChange };
};
