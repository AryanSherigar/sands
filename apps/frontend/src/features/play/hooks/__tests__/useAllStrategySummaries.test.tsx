import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import { useAllStrategySummaries } from "../useAllStrategySummaries";

const SUMMARIES_URL = "*/simulation/v1/playthroughs/pt-1/summaries";
const entry = (id: string, turn: number) => ({
  summary_id: id,
  requested_turn: turn,
  trigger: "major_event",
  status: "completed",
  narration: `Entry ${id}`,
  error_code: null,
  is_retryable: false,
  region_ids: [],
});

describe("useAllStrategySummaries", () => {
  it("follows the paging cursor until the last page", async () => {
    const cursors: (string | null)[] = [];
    server.use(
      http.get(SUMMARIES_URL, ({ request }) => {
        const afterId = new URL(request.url).searchParams.get("after_id");
        cursors.push(afterId);
        if (afterId === null) return HttpResponse.json({ items: [entry("a", 1), entry("b", 2)], next_after_id: "b" });
        return HttpResponse.json({ items: [entry("c", 3)], next_after_id: null });
      }),
    );

    const { result } = renderHook(() => useAllStrategySummaries("pt-1"), { wrapper: createQueryWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.map((item) => item.summary_id)).toEqual(["a", "b", "c"]);
    expect(cursors).toEqual([null, "b"]);
  });
});
