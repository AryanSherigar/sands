import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createScenarioInvite,
  listScenarioAccess,
  removeScenarioAccess,
} from "../api/access.api";
import { ScenarioAccessMember } from "../types/access.types";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import { requireScenarioId } from "../lib/requireScenarioId";

const ACCESS_STALE_TIME_MS = 30_000;

export const useScenarioAccess = (scenarioId: string | null) => {
  const queryClient = useQueryClient();
  const queryKey = ["scenario-access", scenarioId];

  const accessQuery = useQuery<ScenarioAccessMember[], Error>({
    queryKey,
    queryFn: () => listScenarioAccess(requireScenarioId(scenarioId)),
    enabled: Boolean(scenarioId),
    staleTime: ACCESS_STALE_TIME_MS,
  });

  const inviteMutation = useMutation({
    mutationFn: () => createScenarioInvite(requireScenarioId(scenarioId)),
  });

  const removeMutation = useMutation({
    mutationFn: (userId: string) =>
      removeScenarioAccess(requireScenarioId(scenarioId), userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });

  return {
    members: accessQuery.data ?? [],
    isLoading: accessQuery.isLoading,
    error: accessQuery.error,
    createInvite: inviteMutation.mutate,
    createInviteAsync: inviteMutation.mutateAsync,
    isCreatingInvite: inviteMutation.isPending,
    inviteError: inviteMutation.error
      ? extractErrorMessage(inviteMutation.error, "Couldn't create the invite link.")
      : null,
    removeAccess: removeMutation.mutate,
    removeAccessAsync: removeMutation.mutateAsync,
    isRemovingAccess: removeMutation.isPending,
    removeError: removeMutation.error
      ? extractErrorMessage(removeMutation.error, "Couldn't remove access.")
      : null,
  };
};
