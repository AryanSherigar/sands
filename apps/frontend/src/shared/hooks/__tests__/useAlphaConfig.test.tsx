import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import {
  ALPHA_CONFIG,
  NON_ALPHA_CONFIG,
  alphaConfigHandler,
} from "@/test/alphaFixtures";
import { useAlphaConfig } from "../useAlphaConfig";
import { useIsAlphaMode } from "../useIsAlphaMode";

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider
    client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
  >
    {children}
  </QueryClientProvider>
);

describe("useAlphaConfig", () => {
  it("returns the public alpha config", async () => {
    server.use(alphaConfigHandler(ALPHA_CONFIG));
    const { result } = renderHook(() => useAlphaConfig(), { wrapper });
    await waitFor(() => expect(result.current.data).toEqual(ALPHA_CONFIG));
  });
});

describe("useIsAlphaMode", () => {
  it("is false until the config says otherwise", () => {
    server.use(alphaConfigHandler(ALPHA_CONFIG));
    const { result } = renderHook(() => useIsAlphaMode(), { wrapper });
    expect(result.current).toBe(false);
  });

  it("is true once the server reports alpha mode", async () => {
    server.use(alphaConfigHandler(ALPHA_CONFIG));
    const { result } = renderHook(() => useIsAlphaMode(), { wrapper });
    await waitFor(() => expect(result.current).toBe(true));
  });

  it("stays false when the server reports alpha mode off", async () => {
    server.use(alphaConfigHandler(NON_ALPHA_CONFIG));
    const { result } = renderHook(() => useIsAlphaMode(), { wrapper });
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(result.current).toBe(false);
  });
});
