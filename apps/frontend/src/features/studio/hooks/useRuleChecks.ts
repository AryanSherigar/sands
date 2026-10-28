import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createRuleCheck,
  deleteRuleCheck,
  listRuleChecks,
  reorderRuleChecks,
  updateRuleCheck,
} from "../api/ruleChecks.api";
import {
  RuleCheckCreate,
  RuleCheckListResponse,
  RuleCheckUpdate,
} from "../types/ruleCheck.types";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import { requireScenarioId } from "../lib/requireScenarioId";
import { runChildWrite } from "../lib/childWrite";

const AUTHORING_STALE_TIME_MS = 15_000;
const SAVE_FAILURE = "Failed to save rule check.";

const ruleChecksQueryKey = (scenarioId: string | null) => [
  "rule-checks",
  scenarioId,
];

export const useRuleChecks = (scenarioId: string | null) => {
  const queryClient = useQueryClient();
  const guardedWrite = <T,>(write: () => Promise<T>): Promise<T> =>
    runChildWrite(queryClient, requireScenarioId(scenarioId), write);
  const queryKey = ruleChecksQueryKey(scenarioId);
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey });
    queryClient.invalidateQueries({ queryKey: ["scenario", scenarioId] });
    queryClient.invalidateQueries({ queryKey: ["scenario-tools", scenarioId] });
  };

  const query = useQuery<RuleCheckListResponse, Error>({
    queryKey,
    queryFn: () => listRuleChecks(requireScenarioId(scenarioId)),
    enabled: Boolean(scenarioId),
    staleTime: AUTHORING_STALE_TIME_MS,
    refetchOnWindowFocus: true,
  });

  const createMutation = useMutation({
    mutationFn: (payload: RuleCheckCreate) =>
      guardedWrite(() => createRuleCheck(requireScenarioId(scenarioId), payload)),
    onSuccess: invalidate,
  });
  const updateMutation = useMutation({
    mutationFn: ({
      checkId,
      payload,
    }: {
      checkId: string;
      payload: RuleCheckUpdate;
    }) => guardedWrite(() => updateRuleCheck(requireScenarioId(scenarioId), checkId, payload)),
    onSuccess: invalidate,
  });
  const deleteMutation = useMutation({
    mutationFn: (checkId: string) =>
      guardedWrite(() => deleteRuleCheck(requireScenarioId(scenarioId), checkId)),
    onSuccess: invalidate,
  });
  const reorderMutation = useMutation({
    mutationFn: (orderedCheckIds: string[]) =>
      guardedWrite(() => reorderRuleChecks(requireScenarioId(scenarioId), orderedCheckIds)),
    onSuccess: (updated) => queryClient.setQueryData(queryKey, updated),
  });

  return {
    checks: query.data?.items ?? [],
    isLoading: query.isLoading,
    createCheck: createMutation.mutate,
    isCreating: createMutation.isPending,
    createError: createMutation.error
      ? extractErrorMessage(createMutation.error, SAVE_FAILURE)
      : null,
    updateCheck: updateMutation.mutate,
    isUpdating: updateMutation.isPending,
    updateError: updateMutation.error
      ? extractErrorMessage(updateMutation.error, SAVE_FAILURE)
      : null,
    deleteCheck: deleteMutation.mutate,
    reorderChecks: reorderMutation.mutate,
  };
};
