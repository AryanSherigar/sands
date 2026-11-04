import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useStrategyChronicleBook } from "../useStrategyChronicleBook";
import { MAX_BOOK_GENERATED_ENTRIES } from "../../components/StrategyChronicleBook/strategyBook.constants";
import type { StrategySummaryView } from "../../types/simulation.types";

const start = vi.fn();
let items: StrategySummaryView[] = [];
let streaming: { summaryId: string; narration: string; isStreaming: boolean } | null = null;

vi.mock("../useAllStrategySummaries", () => ({
  useAllStrategySummaries: () => ({ isSuccess: true, isLoading: false, data: items }),
}));
vi.mock("../useStrategySummaries", () => ({
  useStrategySummaryStream: () => ({ start, streaming, error: null }),
}));

function summary(id: string, turn: number, status: StrategySummaryView["status"]): StrategySummaryView {
  return {
    summary_id: id,
    requested_turn: turn,
    trigger: "major_event",
    status,
    narration: status === "completed" ? `Entry ${id}` : null,
    error_code: null,
    is_retryable: status !== "completed",
    region_ids: [],
  };
}

describe("useStrategyChronicleBook", () => {
  beforeEach(() => {
    start.mockReset();
    streaming = null;
    items = [];
  });

  it("lists completed entries as chapters in turn order", () => {
    items = [summary("b", 9, "completed"), summary("a", 3, "completed")];
    const { result } = renderHook(() => useStrategyChronicleBook("pt-1"));
    expect(result.current.chapters.map((chapter) => chapter.summaryId)).toEqual(["a", "b"]);
    expect(result.current.chapters[0].narration).toBe("Entry a");
    expect(start).not.toHaveBeenCalled();
    expect(result.current.isPreparing).toBe(false);
  });

  it("generates missing entries up to the cap, oldest first", async () => {
    items = Array.from({ length: MAX_BOOK_GENERATED_ENTRIES + 1 }, (_, index) =>
      summary(`s${index}`, index + 1, "pending"),
    );
    renderHook(() => useStrategyChronicleBook("pt-1"));
    await waitFor(() => expect(start).toHaveBeenCalledTimes(MAX_BOOK_GENERATED_ENTRIES));
    expect(start.mock.calls[0][0].summary_id).toBe("s0");
    expect(start.mock.calls.map((call) => call[0].summary_id)).not.toContain(
      `s${MAX_BOOK_GENERATED_ENTRIES}`,
    );
  });

  it("skips an entry that stays unwritten and keeps the rest of the book", async () => {
    items = [summary("a", 1, "completed"), summary("b", 2, "failed")];
    const { result } = renderHook(() => useStrategyChronicleBook("pt-1"));
    await waitFor(() => expect(start).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(result.current.isPreparing).toBe(false));
    expect(result.current.chapters.map((chapter) => chapter.summaryId)).toEqual(["a"]);
  });

  it("is preparing while an entry is being written", () => {
    items = [summary("a", 1, "completed")];
    streaming = { summaryId: "a", narration: "Wri", isStreaming: true };
    const { result } = renderHook(() => useStrategyChronicleBook("pt-1"));
    expect(result.current.isPreparing).toBe(true);
  });

  it("has no chapters and is not preparing when no entries exist", () => {
    const { result } = renderHook(() => useStrategyChronicleBook("pt-1"));
    expect(result.current.chapters).toEqual([]);
    expect(result.current.isPreparing).toBe(false);
  });
});
