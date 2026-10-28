import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createScenarioEntityType,
  deleteScenarioEntityType,
  listScenarioEntityTypes,
  updateScenarioEntityType,
} from "../api/scenario_entity_types.api";
import {
  ScenarioEntityTypeCreate,
  ScenarioEntityTypeListResponse,
  ScenarioEntityTypeUpdate,
} from "../types/scenario_entity_type.types";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import { requireScenarioId } from "../lib/requireScenarioId";
import { runChildWrite } from "../lib/childWrite";

export const useScenarioEntityTypes = (scenarioId: string | null) => {
  const queryClient = useQueryClient();
  const guardedWrite = <T,>(write: () => Promise<T>): Promise<T> =>
    runChildWrite(queryClient, requireScenarioId(scenarioId), write);
  const queryKey = ["scenario-entity-types", scenarioId];
  const invalidate = () => queryClient.invalidateQueries({ queryKey });

  const entityTypesQuery = useQuery<ScenarioEntityTypeListResponse, Error>({
    queryKey,
    queryFn: () => listScenarioEntityTypes(scenarioId as string),
    enabled: Boolean(scenarioId),
  });

  const createMutation = useMutation({
    mutationFn: (payload: ScenarioEntityTypeCreate) =>
      guardedWrite(() => createScenarioEntityType(requireScenarioId(scenarioId), payload)),
    onSuccess: invalidate,
  });

  const updateMutation = useMutation({
    mutationFn: ({
      scenarioEntityTypeId,
      payload,
    }: {
      scenarioEntityTypeId: string;
      payload: ScenarioEntityTypeUpdate;
    }) =>
      guardedWrite(() => updateScenarioEntityType(
        requireScenarioId(scenarioId),
        scenarioEntityTypeId,
        payload,
      )),
    onSuccess: invalidate,
  });

  const deleteMutation = useMutation({
    mutationFn: (scenarioEntityTypeId: string) =>
      guardedWrite(() => deleteScenarioEntityType(
        requireScenarioId(scenarioId),
        scenarioEntityTypeId,
      )),
    onSuccess: invalidate,
  });

  return {
    entityTypes: entityTypesQuery.data?.items ?? [],
    isLoading: entityTypesQuery.isLoading,
    error: entityTypesQuery.error,
    createEntityType: createMutation.mutate,
    createEntityTypeAsync: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    createError: createMutation.error
      ? extractErrorMessage(createMutation.error, "Failed to save entity type.")
      : null,
    updateEntityType: updateMutation.mutate,
    isUpdating: updateMutation.isPending,
    updateError: updateMutation.error
      ? extractErrorMessage(updateMutation.error, "Failed to save entity type.")
      : null,
    deleteEntityType: deleteMutation.mutate,
    isDeleting: deleteMutation.isPending,
    deleteError: deleteMutation.error
      ? extractErrorMessage(
          deleteMutation.error,
          "Failed to delete entity type.",
        )
      : null,
  };
};
