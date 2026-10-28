import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import type { UserResponse } from "@/features/auth/types/auth.types";
import { useProfileEndings } from "../hooks/useProfileEndings";

const body = { scenarios: [] };

const makeWrapper = (client: QueryClient) =>
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
  };

describe("useProfileEndings", () => {
  it("fetches the owner endings", async () => {
    server.use(
      http.get("*/v1/users/me/endings", () => HttpResponse.json(body)),
    );
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result } = renderHook(() => useProfileEndings(), {
      wrapper: makeWrapper(client),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(body);
  });

  it("surfaces failures as an error state", async () => {
    server.use(
      http.get(
        "*/v1/users/me/endings",
        () => new HttpResponse(null, { status: 500 }),
      ),
    );
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result } = renderHook(() => useProfileEndings(), {
      wrapper: makeWrapper(client),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("never shows a previous account's cached endings to the next user", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    useAuthStore.setState({
      user: { user_id: "user-a" } as unknown as UserResponse,
    });
    server.use(
      http.get("*/v1/users/me/endings", () => HttpResponse.json(body)),
    );
    const { result, rerender } = renderHook(() => useProfileEndings(), {
      wrapper: makeWrapper(client),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    server.use(http.get("*/v1/users/me/endings", () => new Promise(() => {})));
    useAuthStore.setState({
      user: { user_id: "user-b" } as unknown as UserResponse,
    });
    rerender();

    expect(result.current.data).toBeUndefined();
    useAuthStore.setState({ user: null });
  });
});
