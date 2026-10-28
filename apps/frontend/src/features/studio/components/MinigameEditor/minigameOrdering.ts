import { reorderIds } from "../../lib/priorityOrdering";
import { MinigameResponse } from "../../types/minigame.types";

export { sortByPriority } from "../../lib/priorityOrdering";

export const buildReorderedIds = (
  orderedMinigames: MinigameResponse[],
  activeId: string,
  overId: string,
): string[] =>
  reorderIds(
    orderedMinigames.map((item) => item.minigame_id),
    activeId,
    overId,
  );
