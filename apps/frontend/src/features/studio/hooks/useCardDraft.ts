import { useEffect, useMemo, useRef } from "react";
import {
  CardDraft,
  addTrigger,
  buildCardDraft,
  buildEntityUpdate,
  removeTrigger,
  renameTrigger,
} from "../lib/cardDraft";
import type { EntityResponse, EntityUpdate } from "../types/entity.types";
import type { LoreDocument } from "../types/lore.types";
import { useCardAutosave } from "./useCardAutosave";
import { useServerSyncedState } from "./useServerSyncedState";

export const useCardDraft = (
  entity: EntityResponse | undefined,
  saveUpdate: (payload: EntityUpdate) => Promise<unknown>,
) => {
  const serverDraft = useMemo(
    () => (entity ? buildCardDraft(entity) : undefined),
    [entity],
  );
  const [draft, setDraft] = useServerSyncedState<CardDraft>(serverDraft);
  const lastNamedRef = useRef("");
  const { schedule, retry, hasError } = useCardAutosave((next) =>
    saveUpdate(buildEntityUpdate(next)),
  );

  useEffect(() => {
    if (draft?.name.trim()) lastNamedRef.current = draft.name;
  }, [draft?.name]);

  const commit = (next: CardDraft): void => {
    setDraft(next);
    if (next.name.trim()) schedule(next);
  };

  const setName = (name: string): void => {
    if (!draft) return;
    const isNamed = name.trim().length > 0;
    const aliases = isNamed
      ? renameTrigger(draft.aliases, lastNamedRef.current, name)
      : draft.aliases;
    if (isNamed) lastNamedRef.current = name;
    commit({ ...draft, name, aliases });
  };

  const setLore = (lore: LoreDocument): void => {
    if (draft) commit({ ...draft, lore });
  };

  const handleAddTrigger = (trigger: string): void => {
    if (draft) commit({ ...draft, aliases: addTrigger(draft.aliases, trigger) });
  };

  const handleRemoveTrigger = (trigger: string): void => {
    if (draft) commit({ ...draft, aliases: removeTrigger(draft.aliases, trigger) });
  };

  return {
    draft,
    hasError,
    retry,
    setName,
    setLore,
    addTrigger: handleAddTrigger,
    removeTrigger: handleRemoveTrigger,
  };
};
