import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import type { UserResponse } from "@/features/auth/types/auth.types";
import { useProfileAchievements } from "../hooks/useProfileAchievements";

const ownerBody = [
  {
    key: "wayfarer",
    name: "Wayfarer",
    family: "Journey",
    requirement: "Take 100 turns",
    earned_at: null,
    progress: { current: 63, target: 100 },
  },
];
const publicBody = [
  {
    key: "first-steps",
    name: "First Steps",
    family: "Journey",
    requirement: "Take your first turn",
    earned_at: "2026-10-27T00:00:00Z",
  },
];

const makeClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false } } });

const makeWrapper = (client: QueryClient) =>
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
  };

describe("useProfileAchievements", () => {
  it("reads the owner endpoint and keeps progress", async () => {
    server.use(
      http.get("*/v1/users/me/achievements", () =>
        HttpResponse.json(ownerBody),
      ),
    );
    const { result } = renderHook(() => useProfileAchievements("u-1", true), {
      wrapper: makeWrapper(makeClient()),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.[0].progress).toEqual({
      current: 63,
      target: 100,
    });
  });

  it("reads the public endpoint and yields no progress", async () => {
    server.use(
      http.get("*/v1/users/u-2/achievements", () =>
        HttpResponse.json(publicBody),
      ),
    );
    const { result } = renderHook(() => useProfileAchievements("u-2", false), {
      wrapper: makeWrapper(makeClient()),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.[0].progress).toBeNull();
    expect(result.current.data?.[0].earned_at).toBe("2026-10-27T00:00:00Z");
  });

  it("surfaces failures as an error state", async () => {
    server.use(
      http.get(
        "*/v1/users/me/achievements",
        () => new HttpResponse(null, { status: 500 }),
      ),
    );
    const { result } = renderHook(() => useProfileAchievements("u-1", true), {
      wrapper: makeWrapper(makeClient()),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("never shows a previous account's cached owner badges to the next user", async () => {
    const client = makeClient();
    useAuthStore.setState({
      user: { user_id: "user-a" } as unknown as UserResponse,
    });
    server.use(
      http.get("*/v1/users/me/achievements", () =>
        HttpResponse.json(ownerBody),
      ),
    );
    const { result, rerender } = renderHook(
      () => useProfileAchievements("user-a", true),
      { wrapper: makeWrapper(client) },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    server.use(
      http.get("*/v1/users/me/achievements", () => new Promise(() => {})),
    );
    useAuthStore.setState({
      user: { user_id: "user-b" } as unknown as UserResponse,
    });
    rerender();

    expect(result.current.data).toBeUndefined();
    useAuthStore.setState({ user: null });
  });
});
