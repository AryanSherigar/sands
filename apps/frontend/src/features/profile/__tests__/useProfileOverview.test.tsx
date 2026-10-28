import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import type { UserResponse } from "@/features/auth/types/auth.types";
import { overviewBody } from "./fixtures/overview";
import { useProfileOverview } from "../hooks/useProfileOverview";

const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider
    client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
  >
    {children}
  </QueryClientProvider>
);

describe("useProfileOverview", () => {
  it("fetches the owner overview", async () => {
    server.use(
      http.get("*/v1/users/me/overview", () =>
        HttpResponse.json({
          lifetime_stats: {
            turns_taken: 5,
            stories_completed: 1,
            endings_found: 1,
            endings_total: 2,
            worlds_played: 2,
            campaigns_count: 3,
            genres_explored: ["Sci-Fi"],
          },
          weekly_activity: {
            week_start: "2026-10-27",
            played_days: [true, false, false, false, false, false, false],
            played_day_count: 1,
          },
          continue_runs: [],
          recent_milestones: [],
        }),
      ),
    );
    const { result } = renderHook(() => useProfileOverview(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.lifetime_stats.turns_taken).toBe(5);
  });

  it("surfaces failures as an error state", async () => {
    server.use(
      http.get(
        "*/v1/users/me/overview",
        () => new HttpResponse(null, { status: 500 }),
      ),
    );
    const { result } = renderHook(() => useProfileOverview(), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("never shows a previous account's cached overview to the next user", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const sharedWrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    useAuthStore.setState({ user: { user_id: "user-a" } as unknown as UserResponse });
    server.use(
      http.get("*/v1/users/me/overview", () => HttpResponse.json(overviewBody)),
    );
    const { result, rerender } = renderHook(() => useProfileOverview(), {
      wrapper: sharedWrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    server.use(
      http.get("*/v1/users/me/overview", () => new Promise(() => {})),
    );
    useAuthStore.setState({ user: { user_id: "user-b" } as unknown as UserResponse });
    rerender();

    expect(result.current.data).toBeUndefined();
    useAuthStore.setState({ user: null });
  });
});
