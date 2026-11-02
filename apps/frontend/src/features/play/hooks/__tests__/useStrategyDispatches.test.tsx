import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import { useStrategyDispatches } from "../useStrategyDispatches";

const DISPATCH = {
  rumor_id: "rumor_1",
  turn: 3,
  agent: { name: "Aldous", traits: ["honest"] },
  about_faction_id: "house_dunwick",
  topic: "will",
  status: "pending",
  narration: null,
  fallback_line_key: "will.high",
  error_code: null,
};

describe("useStrategyDispatches", () => {
  it("loads the dispatch list from the simulation service", async () => {
    server.use(
      http.get("*/simulation/v1/playthroughs/pt-1/dispatches", () =>
        HttpResponse.json([DISPATCH]),
      ),
    );
    const { result } = renderHook(() => useStrategyDispatches("pt-1"), {
      wrapper: createQueryWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.[0]?.agent.name).toBe("Aldous");
  });

  it("does not fetch without a playthrough id", () => {
    const { result } = renderHook(() => useStrategyDispatches(undefined), {
      wrapper: createQueryWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
  });
});
