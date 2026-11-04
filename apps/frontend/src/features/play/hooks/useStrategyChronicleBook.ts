import { useEffect, useMemo, useState } from "react";
import { MAX_BOOK_GENERATED_ENTRIES } from "../components/StrategyChronicleBook/strategyBook.constants";
import type { StrategySummaryView } from "../types/simulation.types";
import { useAllStrategySummaries } from "./useAllStrategySummaries";
import { useStrategySummaryStream } from "./useStrategySummaries";

export interface BookChapterView {
  summaryId: string;
  turn: number;
  narration: string;
}

export interface UseStrategyChronicleBookReturn {
  chapters: BookChapterView[];
  isPreparing: boolean;
}

const byTurnThenId = (left: StrategySummaryView, right: StrategySummaryView): number =>
  left.requested_turn - right.requested_turn || left.summary_id.localeCompare(right.summary_id);

function toChapters(items: StrategySummaryView[]): BookChapterView[] {
  return items
    .filter((item) => item.status === "completed" && Boolean(item.narration))
    .sort(byTurnThenId)
    .map((item) => ({
      summaryId: item.summary_id,
      turn: item.requested_turn,
      narration: item.narration ?? "",
    }));
}

function findNextMissing(
  items: StrategySummaryView[],
  attemptedIds: string[],
): StrategySummaryView | null {
  if (attemptedIds.length >= MAX_BOOK_GENERATED_ENTRIES) return null;
  const missing = items
    .filter((item) => item.status !== "completed" && !attemptedIds.includes(item.summary_id))
    .sort(byTurnThenId);
  return missing[0] ?? null;
}

export function useStrategyChronicleBook(playthroughId?: string): UseStrategyChronicleBookReturn {
  const summaries = useAllStrategySummaries(playthroughId);
  const stream = useStrategySummaryStream(playthroughId);
  const [attemptedIds, setAttemptedIds] = useState<string[]>([]);
  const items = summaries.data;
  const isWriting = stream.streaming?.isStreaming === true;
  const startEntry = stream.start;
  const chapters = useMemo(() => toChapters(items ?? []), [items]);
  const nextMissing = useMemo(
    () => findNextMissing(items ?? [], attemptedIds),
    [items, attemptedIds],
  );

  useEffect(() => {
    if (!summaries.isSuccess || isWriting || !nextMissing) return;
    setAttemptedIds((current) => [...current, nextMissing.summary_id]);
    startEntry(nextMissing);
  }, [summaries.isSuccess, isWriting, nextMissing, startEntry]);

  return { chapters, isPreparing: isWriting || nextMissing !== null };
}
