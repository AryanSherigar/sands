import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { DEFAULT_PREVIEW_WORLD } from "../../components/StrategyPlayScreen/defaultPreviewWorld";
import { useStrategyPlayStore } from "../../stores/strategyPlay.store";
import { useRestoredTurnReport } from "../useRestoredTurnReport";

const BASE = "/simulation/v1/playthroughs/pt-1";
const REGION_NAMES = {};
const WORLD = { ...DEFAULT_PREVIEW_WORLD, turn: 3 };

const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    {children}
  </QueryClientProvider>
);

describe("useRestoredTurnReport", () => {
  beforeEach(() => {
    useStrategyPlayStore.getState().setLatestReport(null);
  });

  it("restores the last completed turn's report after a reload", async () => {
    server.use(
      http.get(`${BASE}/turns/2/report`, () =>
        HttpResponse.json({
          turn: 2,
          net_gold: 41,
          economy: [],
          battles: [],
          lines: [],
          major_event_kinds: [],
        }),
      ),
    );

    renderHook(() => useRestoredTurnReport("pt-1", WORLD, REGION_NAMES), { wrapper });

    await waitFor(() => expect(useStrategyPlayStore.getState().latestReport).not.toBeNull());
    expect(useStrategyPlayStore.getState().latestReport?.quickStats.netGold).toBe(41);
  });

  it("leaves the store empty when the report cannot be fetched", async () => {
    server.use(http.get(`${BASE}/turns/2/report`, () => HttpResponse.json({}, { status: 404 })));

    renderHook(() => useRestoredTurnReport("pt-1", WORLD, REGION_NAMES), { wrapper });

    await new Promise((resolve) => setTimeout(resolve, 100));
    expect(useStrategyPlayStore.getState().latestReport).toBeNull();
  });
});
