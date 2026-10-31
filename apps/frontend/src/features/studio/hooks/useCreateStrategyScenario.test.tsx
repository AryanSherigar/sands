import { act, renderHook } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import { useCreateStrategyScenario } from "./useCreateStrategyScenario";

describe("useCreateStrategyScenario", () => {
  it("starts new scenarios with the Studio default end year of 1004", async () => {
    let body: { strategy_document?: { tuning?: { end_year?: number } } } = {};
    server.use(
      http.post("*/v1/scenarios", async ({ request }) => {
        body = (await request.json()) as typeof body;
        return HttpResponse.json({ scenario_id: "new-1" }, { status: 201 });
      }),
    );
    const { result } = renderHook(() => useCreateStrategyScenario(), { wrapper: createQueryWrapper() });

    await act(async () => {
      await result.current.mutateAsync();
    });

    expect(body.strategy_document?.tuning?.end_year).toBe(1004);
  });
});
