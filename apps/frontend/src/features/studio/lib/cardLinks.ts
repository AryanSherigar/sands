import {
  FALLBACK_LINK_SUGGESTIONS,
  LINK_SUGGESTIONS,
  buildSuggestionKey,
} from "../constants/linkSuggestions";
import type { CardKind } from "../types/card.types";
import type { EntityResponse } from "../types/entity.types";
import type { FactResponse } from "../types/fact.types";
import type { QuestionGroup } from "../types/guide.types";
import type { LoreDocument } from "../types/lore.types";

export interface PickLinkTarget {
  predicate: string;
  pickedName: string;
}

const isLinkOf = (fact: FactResponse, entityId: string): boolean =>
  fact.object_entity_id !== null &&
  (fact.subject_entity_id === entityId || fact.object_entity_id === entityId);

const isTextLinkOf = (fact: FactResponse, entityId: string): boolean =>
  fact.object_entity_id === null &&
  fact.object_literal !== null &&
  fact.subject_entity_id === entityId;

const normalizeName = (name: string): string => name.trim().toLowerCase();

export const getLinksForEntity = (
  facts: FactResponse[],
  entityId: string,
  shouldIncludeTextLinks = false,
): FactResponse[] =>
  facts.filter(
    (fact) =>
      isLinkOf(fact, entityId) ||
      (shouldIncludeTextLinks && isTextLinkOf(fact, entityId)),
  );

export const getLinkSuggestions = (
  subjectKind: CardKind,
  objectKind: CardKind,
): string[] =>
  LINK_SUGGESTIONS[buildSuggestionKey(subjectKind, objectKind)] ??
  FALLBACK_LINK_SUGGESTIONS;

export const findPickFact = (
  facts: FactResponse[],
  subjectId: string,
  entities: EntityResponse[],
  target: PickLinkTarget,
): FactResponse | undefined => {
  const targetEntity = entities.find(
    (entity) => normalizeName(entity.canonical_name) === normalizeName(target.pickedName),
  );
  if (!targetEntity) return undefined;
  const candidates = facts.filter(
    (fact) =>
      fact.subject_entity_id === subjectId &&
      fact.object_entity_id === targetEntity.entity_id,
  );
  return (
    candidates.find((fact) => fact.predicate === target.predicate) ??
    candidates[0]
  );
};

export const findPickBlockIndex = (
  document: LoreDocument,
  groups: QuestionGroup[],
  predicate: string,
  pickedName: string,
): number => {
  const questionIds = groups
    .flatMap((group) => group.questions)
    .filter((question) => question.pick?.predicate === predicate)
    .map((question) => question.id);
  return document.blocks.findIndex(
    (block) =>
      block.question_id !== null &&
      block.question_id !== undefined &&
      questionIds.includes(block.question_id) &&
      normalizeName(block.text) === normalizeName(pickedName),
  );
};

export interface LinkView {
  fact: FactResponse;
  subject: EntityResponse | undefined;
  object: EntityResponse | undefined;
}

export const buildLinkViews = (
  facts: FactResponse[],
  entities: EntityResponse[],
  entityId: string,
  shouldIncludeTextLinks = false,
): LinkView[] =>
  getLinksForEntity(facts, entityId, shouldIncludeTextLinks).map((fact) => ({
    fact,
    subject: entities.find((entity) => entity.entity_id === fact.subject_entity_id),
    object: entities.find((entity) => entity.entity_id === fact.object_entity_id),
  }));

export const describeLink = (view: LinkView): string =>
  `${view.subject?.canonical_name ?? "Missing card"} ${view.fact.predicate} ${view.object?.canonical_name ?? view.fact.object_literal ?? "Missing card"}`;
