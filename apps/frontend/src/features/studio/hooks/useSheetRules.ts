import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createSheetRule,
  deleteSheetRule,
  listSheetRules,
  reorderSheetRules,
  updateSheetRule,
} from "../api/sheetRules.api";
import {
  SheetRuleCreate,
  SheetRuleListResponse,
  SheetRuleUpdate,
} from "../types/sheetRule.types";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import { requireScenarioId } from "../lib/requireScenarioId";
import { runChildWrite } from "../lib/childWrite";

const AUTHORING_STALE_TIME_MS = 15_000;
const SAVE_FAILURE = "Failed to save rule.";

const sheetRulesQueryKey = (scenarioId: string | null) => [
  "sheet-rules",
  scenarioId,
];

export const useSheetRules = (scenarioId: string | null) => {
  const queryClient = useQueryClient();
  const guardedWrite = <T,>(write: () => Promise<T>): Promise<T> =>
    runChildWrite(queryClient, requireScenarioId(scenarioId), write);
  const queryKey = sheetRulesQueryKey(scenarioId);
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey });
    queryClient.invalidateQueries({ queryKey: ["scenario-tools", scenarioId] });
  };

  const query = useQuery<SheetRuleListResponse, Error>({
    queryKey,
    queryFn: () => listSheetRules(requireScenarioId(scenarioId)),
    enabled: Boolean(scenarioId),
    staleTime: AUTHORING_STALE_TIME_MS,
    refetchOnWindowFocus: true,
  });

  const createMutation = useMutation({
    mutationFn: (payload: SheetRuleCreate) =>
      guardedWrite(() => createSheetRule(requireScenarioId(scenarioId), payload)),
    onSuccess: invalidate,
  });
  const updateMutation = useMutation({
    mutationFn: ({
      ruleId,
      payload,
    }: {
      ruleId: string;
      payload: SheetRuleUpdate;
    }) => guardedWrite(() => updateSheetRule(requireScenarioId(scenarioId), ruleId, payload)),
    onSuccess: invalidate,
  });
  const deleteMutation = useMutation({
    mutationFn: (ruleId: string) =>
      guardedWrite(() => deleteSheetRule(requireScenarioId(scenarioId), ruleId)),
    onSuccess: invalidate,
  });
  const reorderMutation = useMutation({
    mutationFn: (orderedRuleIds: string[]) =>
      guardedWrite(() => reorderSheetRules(requireScenarioId(scenarioId), orderedRuleIds)),
    onSuccess: (updated) => queryClient.setQueryData(queryKey, updated),
  });

  return {
    rules: query.data?.items ?? [],
    isLoading: query.isLoading,
    createRule: createMutation.mutate,
    isCreating: createMutation.isPending,
    createError: createMutation.error
      ? extractErrorMessage(createMutation.error, SAVE_FAILURE)
      : null,
    updateRule: updateMutation.mutate,
    isUpdating: updateMutation.isPending,
    updateError: updateMutation.error
      ? extractErrorMessage(updateMutation.error, SAVE_FAILURE)
      : null,
    deleteRule: deleteMutation.mutate,
    reorderRules: reorderMutation.mutate,
  };
};
