import { findPickBlockIndex, findPickFact } from "../lib/cardLinks";
import { removeBlock } from "../lib/loreDocument";
import type { EntityResponse } from "../types/entity.types";
import type { FactResponse } from "../types/fact.types";
import type { GuideQuestion, PickOption, QuestionGroup } from "../types/guide.types";
import type { LoreDocument } from "../types/lore.types";

interface CardPickLinksOptions {
  entityId: string;
  questions: QuestionGroup[];
  facts: FactResponse[];
  entities: EntityResponse[];
  lore: LoreDocument | undefined;
  setLore: (lore: LoreDocument) => void;
  createLink: (otherEntityId: string, predicate: string) => Promise<unknown>;
  deleteLink: (fact: FactResponse) => Promise<unknown>;
}

export const useCardPickLinks = ({
  entityId,
  questions,
  facts,
  entities,
  lore,
  setLore,
  createLink,
  deleteLink,
}: CardPickLinksOptions) => {
  const handlePick = (question: GuideQuestion, option: PickOption): void => {
    if (question.pick) void createLink(option.id, question.pick.predicate);
  };

  const handleRemovePick = (question: GuideQuestion, pickedName: string): void => {
    if (!question.pick) return;
    const fact = findPickFact(facts, entityId, entities, {
      predicate: question.pick.predicate,
      pickedName,
    });
    if (fact) void deleteLink(fact);
  };

  const handleDeleteLink = async (fact: FactResponse): Promise<void> => {
    await deleteLink(fact);
    const targetName = entities.find(
      (entity) => entity.entity_id === fact.object_entity_id,
    )?.canonical_name;
    if (!lore || !targetName || fact.subject_entity_id !== entityId) return;
    const index = findPickBlockIndex(lore, questions, fact.predicate, targetName);
    if (index >= 0) setLore(removeBlock(lore, index));
  };

  return { handlePick, handleRemovePick, handleDeleteLink };
};
