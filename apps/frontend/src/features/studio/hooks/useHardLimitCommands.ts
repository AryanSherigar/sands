import { useCallback } from "react";
import { HARD_LIMIT_EXAMPLES } from "../constants/hardLimits";
import { buildLimitCopy, buildNewLimit } from "../lib/limitDraft";
import { buildLimitFromExample } from "../lib/limitExamples";
import type { InvariantResponse, InvariantUpdate } from "../types/invariant.types";
import type { ValueOption } from "../types/sentence.types";
import { useGuide } from "./useGuide";
import { useInvariants } from "./useInvariants";

interface HardLimitCommands {
  limits: InvariantResponse[];
  isLoading: boolean;
  addLimit: () => void;
  duplicateLimit: (row: InvariantResponse) => void;
  addExample: (exampleId: string) => void;
  updateLimit: (invariantId: string, payload: InvariantUpdate) => void;
  deleteLimit: (invariantId: string) => void;
}

export const useHardLimitCommands = (options: readonly ValueOption[]): HardLimitCommands => {
  const { scenarioId } = useGuide();
  const limits = useInvariants(scenarioId);
  const { createInvariant, updateInvariant, deleteInvariant } = limits;

  const addLimit = useCallback((): void => createInvariant(buildNewLimit()), [createInvariant]);
  const duplicateLimit = useCallback(
    (row: InvariantResponse): void => createInvariant(buildLimitCopy(row)),
    [createInvariant],
  );
  const addExample = useCallback(
    (exampleId: string): void => {
      const example = HARD_LIMIT_EXAMPLES.find((candidate) => candidate.id === exampleId);
      if (example) createInvariant(buildLimitFromExample(example, options));
    },
    [createInvariant, options],
  );
  const updateLimit = useCallback(
    (invariantId: string, payload: InvariantUpdate): void => updateInvariant({ invariantId, payload }),
    [updateInvariant],
  );

  return {
    limits: limits.invariants,
    isLoading: limits.isLoading,
    addLimit,
    duplicateLimit,
    addExample,
    updateLimit,
    deleteLimit: deleteInvariant,
  };
};
