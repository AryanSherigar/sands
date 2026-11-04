import { useCallback, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { updateScenario } from "../api/scenarios.api";
import { TITLE_MAX_LENGTH } from "../constants/guideLimits";
import { SCENARIO_QUERY_KEY } from "../constants/studioScenario";
import { applyStrategyBlock } from "../lib/strategyChatApply";
import type { ActionBlock } from "../types/assistant.types";
import type { StrategyFields } from "../types/strategyDocument.types";

export interface UseStrategyActionApplierArgs {
  scenarioId: string | null;
  edit: (change: (current: StrategyFields) => StrategyFields) => void;
  knownRegionIds: ReadonlySet<string>;
}

export type ReportStrategyApplyError = (message: string) => void;

export interface StrategyActionApplier {
  applyBatch: (blocks: ActionBlock[], onError: ReportStrategyApplyError) => Promise<boolean[]>;
}

export const useStrategyActionApplier = ({
  scenarioId,
  edit,
  knownRegionIds,
}: UseStrategyActionApplierArgs): StrategyActionApplier => {
  const queryClient = useQueryClient();
  const tempFactionIdsRef = useRef<Map<string, string>>(new Map());

  const applyTitle = useCallback(
    async (block: ActionBlock, onError: ReportStrategyApplyError): Promise<boolean> => {
      const title = block.content.trim();
      if (!scenarioId || !title || title.length > TITLE_MAX_LENGTH) {
        onError(`The title must be 1 to ${TITLE_MAX_LENGTH} characters.`);
        return false;
      }
      try {
        const saved = await updateScenario(scenarioId, { title });
        queryClient.setQueryData([SCENARIO_QUERY_KEY, scenarioId], saved);
        return true;
      } catch {
        onError("Couldn't save the title. Try again.");
        return false;
      }
    },
    [scenarioId, queryClient],
  );

  const applyFieldBlocks = useCallback(
    (blocks: ActionBlock[], onError: ReportStrategyApplyError): boolean[] => {
      const outcomes: boolean[] = [];
      if (blocks.length === 0) return outcomes;
      edit((current) => {
        let next = current;
        for (const block of blocks) {
          const result = applyStrategyBlock(next, block, { knownRegionIds, tempFactionIds: tempFactionIdsRef.current });
          if (result.error !== null) onError(result.error);
          else next = result.fields;
          outcomes.push(result.error === null);
        }
        return next;
      });
      return outcomes;
    },
    [edit, knownRegionIds],
  );

  const applyBatch = useCallback(
    async (blocks: ActionBlock[], onError: ReportStrategyApplyError): Promise<boolean[]> => {
      const fieldBlocks = blocks.filter((block) => block.target !== "title");
      const fieldOutcomes = applyFieldBlocks(fieldBlocks, onError);
      const outcomes: boolean[] = [];
      for (const block of blocks) {
        outcomes.push(block.target === "title" ? await applyTitle(block, onError) : (fieldOutcomes.shift() ?? false));
      }
      return outcomes;
    },
    [applyFieldBlocks, applyTitle],
  );

  return { applyBatch };
};
