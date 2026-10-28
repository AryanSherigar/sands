import { useMemo } from "react";
import { buildLinkViews } from "../lib/cardLinks";
import type { FactResponse, NewLinkInput } from "../types/fact.types";
import { useEntities } from "./useEntities";
import { useFacts } from "./useFacts";

export const useCardLinks = (
  scenarioId: string,
  entityId: string,
  shouldIncludeTextLinks = false,
) => {
  const { entities } = useEntities(scenarioId);
  const {
    facts,
    createFactAsync,
    updateFactAsync,
    deleteFactAsync,
    error,
    createError,
    updateError,
    deleteError,
  } = useFacts(scenarioId);

  const links = useMemo(
    () => buildLinkViews(facts, entities, entityId, shouldIncludeTextLinks),
    [facts, entities, entityId, shouldIncludeTextLinks],
  );

  const createLink = (otherEntityId: string, predicate: string) =>
    createFactAsync({
      subject_entity_id: entityId,
      predicate,
      object_entity_id: otherEntityId,
    });
  const createLinkFrom = (input: NewLinkInput) =>
    createFactAsync({
      subject_entity_id: entityId,
      predicate: input.predicate,
      ...(input.otherEntityId ? { object_entity_id: input.otherEntityId } : {}),
      ...(input.objectLiteral ? { object_literal: input.objectLiteral } : {}),
      ...(input.whenActive ? { when_active: input.whenActive } : {}),
    });
  const setWhenActive = (fact: FactResponse, whenActive: Record<string, unknown> | null) =>
    updateFactAsync({ factId: fact.fact_id, payload: { when_active: whenActive } });
  const updatePredicate = (fact: FactResponse, predicate: string) =>
    updateFactAsync({ factId: fact.fact_id, payload: { predicate } });
  const setSecret = (fact: FactResponse, isSecret: boolean) =>
    updateFactAsync({ factId: fact.fact_id, payload: { hidden: isSecret } });
  const deleteLink = (fact: FactResponse) => deleteFactAsync(fact.fact_id);

  return {
    links,
    facts,
    entities,
    createLink,
    createLinkFrom,
    setWhenActive,
    updatePredicate,
    setSecret,
    deleteLink,
    errorMessage: error?.message ?? createError ?? updateError ?? deleteError,
  };
};
