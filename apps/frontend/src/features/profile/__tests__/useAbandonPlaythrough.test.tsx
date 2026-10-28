import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useAbandonPlaythrough } from "../hooks/useAbandonPlaythrough";
import { overviewBody } from "./fixtures/overview";

describe("useAbandonPlaythrough", () => {
  it("drops the cached overview so a stale Continue card is never shown", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    client.setQueryData(["profile-overview", "user-a"], overviewBody);
    server.use(
      http.post(
        "*/v1/playthroughs/pt-1/abandon",
        () => new HttpResponse(null, { status: 204 }),
      ),
    );
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(() => useAbandonPlaythrough(), { wrapper });

    await act(async () => {
      result.current.mutate("pt-1");
    });

    await waitFor(() =>
      expect(client.getQueryData(["profile-overview", "user-a"])).toBeUndefined(),
    );
  });
});
