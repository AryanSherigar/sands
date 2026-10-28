import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  MapPinCreate,
  MapPinListResponse,
  MapPinUpdate,
  createMapPin,
  deleteMapPin,
  listMapPins,
  updateMapPin,
} from "../api/maps.api";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import { requireScenarioId } from "../lib/requireScenarioId";
import { runChildWrite } from "../lib/childWrite";

export const useMapPins = (scenarioId: string | null, mapId: string | null) => {
  const queryClient = useQueryClient();
  const guardedWrite = <T,>(write: () => Promise<T>): Promise<T> =>
    runChildWrite(queryClient, requireScenarioId(scenarioId), write);
  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: ["map-pins", scenarioId, mapId],
    });

  const pinsQuery = useQuery<MapPinListResponse, Error>({
    queryKey: ["map-pins", scenarioId, mapId],
    queryFn: () => listMapPins(scenarioId as string, mapId as string),
    enabled: Boolean(scenarioId) && Boolean(mapId),
  });

  const createMutation = useMutation({
    mutationFn: (payload: MapPinCreate) =>
      guardedWrite(() => createMapPin(scenarioId as string, mapId as string, payload)),
    onSuccess: invalidate,
  });

  const updateMutation = useMutation({
    mutationFn: ({
      pinId,
      payload,
    }: {
      pinId: string;
      payload: MapPinUpdate;
    }) => guardedWrite(() => updateMapPin(scenarioId as string, mapId as string, pinId, payload)),
    onSuccess: invalidate,
  });

  const deleteMutation = useMutation({
    mutationFn: (pinId: string) =>
      guardedWrite(() => deleteMapPin(scenarioId as string, mapId as string, pinId)),
    onSuccess: invalidate,
  });

  return {
    pins: pinsQuery.data?.items ?? [],
    isLoading: pinsQuery.isLoading,
    createPin: createMutation.mutate,
    isCreating: createMutation.isPending,
    createError: createMutation.error
      ? extractErrorMessage(createMutation.error, "Failed to place pin.")
      : null,
    updatePin: updateMutation.mutate,
    isUpdating: updateMutation.isPending,
    updateError: updateMutation.error
      ? extractErrorMessage(updateMutation.error, "Failed to update pin.")
      : null,
    deletePin: deleteMutation.mutate,
  };
};
