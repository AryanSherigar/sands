import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  createFact,
  deleteFact,
  listFacts,
  updateFact,
} from "../api/facts.api";
import {
  FactCreate,
  FactListResponse,
  FactResponse,
  FactUpdate,
} from "../types/fact.types";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import { requireScenarioId } from "../lib/requireScenarioId";
import { runGuardedWrite, withEditStamp } from "../lib/editGuard";
import { applyScenarioEditStamp } from "../lib/scenarioEditStamp";

const FACTS_STALE_TIME_MS = 30_000;
const SAVE_ERROR_MESSAGE = "Failed to save fact.";

interface FactUpdateRequest {
  factId: string;
  payload: FactUpdate;
}

interface FactDeleteRequest {
  factId: string;
  expectedContentEditedAt?: string;
}

type FactDeleteInput = string | FactDeleteRequest;

const toDeleteRequest = (input: FactDeleteInput): FactDeleteRequest =>
  typeof input === "string" ? { factId: input } : input;

export const useFacts = (
  scenarioId: string | null,
  entityId: string | null = null,
) => {
  const queryClient = useQueryClient();
  const invalidate = (saved?: FactResponse) => {
    applyScenarioEditStamp(queryClient, scenarioId, saved?.scenario_content_edited_at);
    return queryClient.invalidateQueries({ queryKey: ["facts", scenarioId] });
  };

  const factsQuery = useQuery<FactListResponse, Error>({
    queryKey: ["facts", scenarioId, entityId],
    queryFn: () => listFacts(scenarioId as string, entityId),
    enabled: Boolean(scenarioId),
    staleTime: FACTS_STALE_TIME_MS,
  });

  const guardedWrite = <T>(
    write: (stamp: string | undefined) => Promise<T>,
    options?: { shouldRefreshStamp?: boolean },
  ): Promise<T> =>
    runGuardedWrite(queryClient, requireScenarioId(scenarioId), write, options);

  const createMutation = useMutation({
    mutationFn: (payload: FactCreate) =>
      guardedWrite((stamp) =>
        createFact(requireScenarioId(scenarioId), withEditStamp(payload, stamp)),
      ),
    onSuccess: invalidate,
  });

  const updateMutation = useMutation({
    mutationFn: ({ factId, payload }: FactUpdateRequest) =>
      guardedWrite((stamp) =>
        updateFact(
          requireScenarioId(scenarioId),
          factId,
          withEditStamp(payload, stamp),
        ),
      ),
    onSuccess: invalidate,
  });

  const deleteMutation = useMutation({
    mutationFn: (input: FactDeleteInput) => {
      const { factId, expectedContentEditedAt } = toDeleteRequest(input);
      return guardedWrite(
        (stamp) =>
          deleteFact(
            requireScenarioId(scenarioId),
            factId,
            expectedContentEditedAt ?? stamp,
          ),
        { shouldRefreshStamp: true },
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scenario", scenarioId] });
      return invalidate();
    },
  });

  return {
    facts: factsQuery.data?.items ?? [],
    isLoading: factsQuery.isLoading,
    error: factsQuery.error,
    createFact: createMutation.mutate,
    createFactAsync: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    createError: createMutation.error
      ? extractErrorMessage(createMutation.error, SAVE_ERROR_MESSAGE)
      : null,
    updateFact: updateMutation.mutate,
    updateFactAsync: updateMutation.mutateAsync,
    isUpdating: updateMutation.isPending,
    updateError: updateMutation.error
      ? extractErrorMessage(updateMutation.error, SAVE_ERROR_MESSAGE)
      : null,
    deleteFact: deleteMutation.mutate,
    deleteFactAsync: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
    deleteError: deleteMutation.error
      ? extractErrorMessage(deleteMutation.error, SAVE_ERROR_MESSAGE)
      : null,
  };
};
