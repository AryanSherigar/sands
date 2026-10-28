import { NewCardRequest, buildNewCardPayload } from "../lib/cardDraft";
import { useEntities } from "./useEntities";

export const useCreateCard = (scenarioId: string | null) => {
  const { createEntityAsync, isCreating, createError } = useEntities(scenarioId);

  const createCard = (request: NewCardRequest) =>
    createEntityAsync(buildNewCardPayload(request));

  return { createCard, isCreatingCard: isCreating, createCardError: createError };
};
