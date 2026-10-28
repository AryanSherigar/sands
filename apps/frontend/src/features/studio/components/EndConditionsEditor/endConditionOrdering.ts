import { reorderIds } from "../../lib/priorityOrdering";
import { EndConditionResponse } from "../../types/end_condition.types";

export { sortByPriority } from "../../lib/priorityOrdering";

export const buildReorderedIds = (
  orderedEndConditions: EndConditionResponse[],
  activeId: string,
  overId: string,
): string[] =>
  reorderIds(
    orderedEndConditions.map((item) => item.end_condition_id),
    activeId,
    overId,
  );
