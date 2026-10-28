import { useCallback, useMemo } from "react";
import { buildReorderedIds, sortByPriority } from "../components/EndConditionsEditor/endConditionOrdering";
import { buildEndingCopy, buildNewEnding } from "../lib/endingDraft";
import { moveItem } from "@/shared/lib/moveItem";
import type { EndConditionResponse, EndConditionUpdate, OutcomeTag } from "../types/end_condition.types";
import { useEndConditions } from "./useEndConditions";
import { useGuide } from "./useGuide";

interface EndingCommands {
  endings: EndConditionResponse[];
  isLoading: boolean;
  addEnding: (tag: OutcomeTag) => void;
  duplicateEnding: (row: EndConditionResponse) => void;
  updateEnding: (endConditionId: string, payload: EndConditionUpdate) => void;
  deleteEnding: (endConditionId: string) => void;
  moveEnding: (endConditionId: string, offset: -1 | 1) => void;
  dragEnding: (activeId: string, overId: string) => void;
}

export const useEndingCommands = (): EndingCommands => {
  const { scenarioId } = useGuide();
  const endings = useEndConditions(scenarioId);
  const ordered = useMemo(() => sortByPriority(endings.endConditions), [endings.endConditions]);
  const { createEndCondition, updateEndCondition, deleteEndCondition, reorderEndConditions } = endings;

  const nextPriority = ordered.length === 0 ? 0 : Math.max(...ordered.map((row) => row.priority)) + 1;
  const addEnding = useCallback(
    (tag: OutcomeTag): void => createEndCondition(buildNewEnding(tag, nextPriority)),
    [createEndCondition, nextPriority],
  );
  const duplicateEnding = useCallback(
    (row: EndConditionResponse): void => createEndCondition(buildEndingCopy(row, nextPriority)),
    [createEndCondition, nextPriority],
  );
  const updateEnding = useCallback(
    (endConditionId: string, payload: EndConditionUpdate): void =>
      updateEndCondition({ endConditionId, payload }),
    [updateEndCondition],
  );
  const moveEnding = useCallback(
    (endConditionId: string, offset: -1 | 1): void => {
      const index = ordered.findIndex((row) => row.end_condition_id === endConditionId);
      if (index + offset < 0 || index + offset >= ordered.length) return;
      const ids = moveItem(ordered.map((row) => row.end_condition_id), index, index + offset);
      reorderEndConditions(ids);
    },
    [ordered, reorderEndConditions],
  );
  const dragEnding = useCallback(
    (activeId: string, overId: string): void =>
      reorderEndConditions(buildReorderedIds(ordered, activeId, overId)),
    [ordered, reorderEndConditions],
  );

  return {
    endings: ordered,
    isLoading: endings.isLoading,
    addEnding,
    duplicateEnding,
    updateEnding,
    deleteEnding: deleteEndCondition,
    moveEnding,
    dragEnding,
  };
};
