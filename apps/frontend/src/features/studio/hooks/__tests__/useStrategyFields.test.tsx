import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ScenarioResponse } from "../../types/scenario.types";
import { useStrategyFields } from "../useStrategyFields";

const updateScenario = vi.fn();
vi.mock("../../api/scenarios.api", () => ({
  updateScenario: (...args: unknown[]) => updateScenario(...args),
}));

const SCENARIO = { scenario_id: "s1", strategy_document: {} } as ScenarioResponse;

const queryClient = new QueryClient();

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe("useStrategyFields flush", () => {
  beforeEach(() => {
    updateScenario.mockReset();
  });

  it("resolves false and reports a failed save when the API rejects", async () => {
    updateScenario.mockImplementation(async () => {
      throw new Error("network");
    });
    const { result } = renderHook(() => useStrategyFields(SCENARIO), { wrapper });

    act(() => result.current.edit((current) => current));
    let didSave = true;
    await act(async () => {
      didSave = await result.current.flush();
    });

    expect(didSave).toBe(false);
    expect(result.current.saveState).toBe("failed");
  });

  it("resolves true after a successful save", async () => {
    updateScenario.mockResolvedValue(SCENARIO);
    const { result } = renderHook(() => useStrategyFields(SCENARIO), { wrapper });

    act(() => result.current.edit((current) => current));
    let didSave = false;
    await act(async () => {
      didSave = await result.current.flush();
    });

    expect(didSave).toBe(true);
    expect(result.current.saveState).toBe("saved");
  });
});
