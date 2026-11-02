import React from "react";
import { act, renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { SSEHandlers } from "@/shared/lib/sse-client";
import type { StrategyDispatchView } from "../../types/simulation.types";
import { useStrategyDispatchStream } from "../useStrategyDispatchStream";

let handlers: SSEHandlers;
const startConnection = vi.fn();

vi.mock("@/shared/hooks/usePostSSE", () => ({
  usePostSSE: (next: SSEHandlers) => {
    handlers = next;
    return { status: "idle", start: startConnection, stop: vi.fn() };
  },
}));

const DISPATCH: StrategyDispatchView = {
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

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient();
  return (
    <React.StrictMode>
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    </React.StrictMode>
  );
}

describe("useStrategyDispatchStream", () => {
  beforeEach(() => startConnection.mockReset());

  it("streams narration chunks for the dispatch being read", () => {
    const { result } = renderHook(() => useStrategyDispatchStream("pt-1"), { wrapper });
    act(() => result.current.start(DISPATCH));
    act(() => handlers.onEvent("narration", "My lord, "));
    act(() => handlers.onEvent("narration", "all is calm."));
    expect(result.current.streaming).toEqual({ rumorId: "rumor_1", narration: "My lord, all is calm." });
    expect(startConnection).toHaveBeenCalledWith(
      "/trs/v1/strategy/playthroughs/pt-1/dispatches/rumor_1/stream",
      expect.objectContaining({ client_request_id: expect.any(String) }),
    );
  });

  it("records a degraded dispatch exactly once even when an error follows", () => {
    const { result } = renderHook(() => useStrategyDispatchStream("pt-1"), { wrapper });
    act(() => result.current.start(DISPATCH));
    act(() => handlers.onEvent("degraded", "{}"));
    act(() => handlers.onError?.(new Error("closed")));
    expect(result.current.streaming).toBeNull();
    expect(result.current.degradedRumorIds).toEqual(["rumor_1"]);
  });

  it("clears streaming on done", () => {
    const { result } = renderHook(() => useStrategyDispatchStream("pt-1"), { wrapper });
    act(() => result.current.start(DISPATCH));
    act(() => handlers.onEvent("done", "{}"));
    expect(result.current.streaming).toBeNull();
    expect(result.current.degradedRumorIds).toEqual([]);
  });

  it("does not stream a completed dispatch", () => {
    const { result } = renderHook(() => useStrategyDispatchStream("pt-1"), { wrapper });
    act(() => result.current.start({ ...DISPATCH, status: "completed" }));
    expect(startConnection).not.toHaveBeenCalled();
  });
});
