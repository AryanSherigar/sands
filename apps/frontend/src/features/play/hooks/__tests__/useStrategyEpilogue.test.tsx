import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useStrategyEpilogue } from "../useStrategyEpilogue";

const getStrategyEpilogue = vi.fn();
const startStream = vi.fn();
let handlers: { onEvent: (name: string, data: string) => void } | null = null;

vi.mock("../../api/simulation.api", () => ({
  getStrategyEpilogue: (...args: unknown[]) => getStrategyEpilogue(...args),
  getStrategyEpilogueStreamPath: (id: string) => `/trs/v1/strategy/playthroughs/${id}/epilogue/stream`,
}));
vi.mock("@/shared/hooks/usePostSSE", () => ({
  usePostSSE: (nextHandlers: typeof handlers) => {
    handlers = nextHandlers;
    return { status: "idle", start: startStream, stop: vi.fn() };
  },
}));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe("useStrategyEpilogue", () => {
  beforeEach(() => {
    getStrategyEpilogue.mockReset();
    startStream.mockReset();
    handlers = null;
  });

  it("returns the saved closing entry without streaming", async () => {
    getStrategyEpilogue.mockResolvedValue({ status: "completed", narration: "Saved legacy.", is_retryable: false });
    const { result } = renderHook(() => useStrategyEpilogue("pt-1"), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("completed"));
    expect(result.current.narration).toBe("Saved legacy.");
    expect(startStream).not.toHaveBeenCalled();
  });

  it("starts the stream on the epilogue path and shows text as it arrives", async () => {
    getStrategyEpilogue.mockResolvedValue({ status: "pending", narration: null, is_retryable: true });
    const { result } = renderHook(() => useStrategyEpilogue("pt-1"), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("pending"));
    act(() => result.current.start());
    expect(startStream.mock.calls[0][0]).toBe("/trs/v1/strategy/playthroughs/pt-1/epilogue/stream");
    expect(startStream.mock.calls[0][1]).toEqual({ client_request_id: expect.any(String) });
    act(() => handlers?.onEvent("narration", "They "));
    act(() => handlers?.onEvent("narration", "remember."));
    expect(result.current.narration).toBe("They remember.");
    expect(result.current.status).toBe("streaming");
  });

  it("reports a failed entry when the stream sends an error", async () => {
    getStrategyEpilogue.mockResolvedValue({ status: "pending", narration: null, is_retryable: true });
    const { result } = renderHook(() => useStrategyEpilogue("pt-1"), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("pending"));
    act(() => result.current.start());
    act(() =>
      handlers?.onEvent(
        "epilogue_error",
        JSON.stringify({ code: "provider_timeout", message: "Try again.", is_retryable: true }),
      ),
    );
    expect(result.current.status).toBe("failed");
    expect(result.current.errorMessage).toBe("Try again.");
  });
});
