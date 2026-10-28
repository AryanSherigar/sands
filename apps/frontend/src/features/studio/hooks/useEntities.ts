import {
  QueryClient,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  createEntity,
  deleteEntity,
  listEntities,
  updateEntity,
} from "../api/entities.api";
import {
  EntityCreate,
  EntityListResponse,
  EntityResponse,
  EntityUpdate,
} from "../types/entity.types";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import { requireScenarioId } from "../lib/requireScenarioId";
import { runGuardedWrite, withEditStamp } from "../lib/editGuard";
import { applyScenarioEditStamp } from "../lib/scenarioEditStamp";

const ENTITIES_STALE_TIME_MS = 30_000;
const SAVE_ERROR_MESSAGE = "Failed to save entity.";

interface EntityUpdateRequest {
  entityId: string;
  payload: EntityUpdate;
}

interface EntityDeleteRequest {
  entityId: string;
  expectedContentEditedAt?: string;
}

type EntityDeleteInput = string | EntityDeleteRequest;

const toDeleteRequest = (input: EntityDeleteInput): EntityDeleteRequest =>
  typeof input === "string" ? { entityId: input } : input;

const refreshAfterDelete = (
  queryClient: QueryClient,
  scenarioId: string | null,
): void => {
  queryClient.invalidateQueries({ queryKey: ["entities", scenarioId] });
  queryClient.invalidateQueries({ queryKey: ["facts", scenarioId] });
  queryClient.invalidateQueries({ queryKey: ["scenario", scenarioId] });
};

export const useEntities = (scenarioId: string | null) => {
  const queryClient = useQueryClient();
  const invalidate = (saved?: EntityResponse) => {
    applyScenarioEditStamp(queryClient, scenarioId, saved?.scenario_content_edited_at);
    return queryClient.invalidateQueries({ queryKey: ["entities", scenarioId] });
  };

  const entitiesQuery = useQuery<EntityListResponse, Error>({
    queryKey: ["entities", scenarioId],
    queryFn: () => listEntities(scenarioId as string),
    enabled: Boolean(scenarioId),
    staleTime: ENTITIES_STALE_TIME_MS,
  });

  const guardedWrite = <T>(
    write: (stamp: string | undefined) => Promise<T>,
    options?: { shouldRefreshStamp?: boolean },
  ): Promise<T> =>
    runGuardedWrite(queryClient, requireScenarioId(scenarioId), write, options);

  const createMutation = useMutation({
    mutationFn: (payload: EntityCreate) =>
      guardedWrite((stamp) =>
        createEntity(requireScenarioId(scenarioId), withEditStamp(payload, stamp)),
      ),
    onSuccess: invalidate,
  });

  const updateMutation = useMutation({
    mutationFn: ({ entityId, payload }: EntityUpdateRequest) =>
      guardedWrite((stamp) =>
        updateEntity(
          requireScenarioId(scenarioId),
          entityId,
          withEditStamp(payload, stamp),
        ),
      ),
    onSuccess: invalidate,
  });

  const deleteMutation = useMutation({
    mutationFn: (input: EntityDeleteInput) => {
      const { entityId, expectedContentEditedAt } = toDeleteRequest(input);
      return guardedWrite(
        (stamp) =>
          deleteEntity(
            requireScenarioId(scenarioId),
            entityId,
            expectedContentEditedAt ?? stamp,
          ),
        { shouldRefreshStamp: true },
      );
    },
    onSuccess: () => refreshAfterDelete(queryClient, scenarioId),
  });

  return {
    entities: entitiesQuery.data?.items ?? [],
    isLoading: entitiesQuery.isLoading,
    error: entitiesQuery.error,
    createEntity: createMutation.mutate,
    createEntityAsync: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    createError: createMutation.error
      ? extractErrorMessage(createMutation.error, SAVE_ERROR_MESSAGE)
      : null,
    updateEntity: updateMutation.mutate,
    updateEntityAsync: updateMutation.mutateAsync,
    isUpdating: updateMutation.isPending,
    updateError: updateMutation.error
      ? extractErrorMessage(updateMutation.error, SAVE_ERROR_MESSAGE)
      : null,
    deleteEntity: deleteMutation.mutate,
    deleteEntityAsync: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
    deleteError: deleteMutation.error
      ? extractErrorMessage(deleteMutation.error, SAVE_ERROR_MESSAGE)
      : null,
  };
};
