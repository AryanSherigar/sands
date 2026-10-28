import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { apiClient } from "@/shared/lib/api-client";
import { useStrategyEvent } from "../useStrategyEvent";
import type { CampaignWorldView } from "../../types/simulation.types";

vi.mock("@/shared/lib/api-client", () => ({
  apiClient: { get: vi.fn(), post: vi.fn() },
}));

const mockedClient = vi.mocked(apiClient);

const mockWorld: CampaignWorldView = {
  world_version: 1,
  turn: 3,
  wave: 0,
  status: "planning",
  battles: [],
  clock: { turn: 3, start_year: 1042, start_month: 1 },
  my_faction: {
    id: "f1",
    treasury: 100,
    manpower: 1000,
    stability: 2,
    war_exhaustion: 0,
    reputation: 0,
    tax_rate: "normal",
    loans: [],
  },
  ruler: { name: "Lord Alex" },
  regions: [],
  armies: [],
  rivals: [],
  queued_orders: [],
  orders_remaining: 3,
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("useStrategyEvent", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns null eventPackage when not awaiting scene", () => {
    const { result } = renderHook(
      () => useStrategyEvent("pt-1", mockWorld),
      { wrapper: createWrapper() }
    );

    expect(result.current.eventPackage).toBeNull();
    expect(result.current.isResolving).toBe(false);
  });

  it("shows the shortfall dialog for an event-type scene pause", async () => {
    const worldAwaiting: CampaignWorldView = {
      ...mockWorld,
      status: "awaiting_scene",
      scene_id: "scene-shortfall-1",
      pending_scene: { scene_id: "scene-shortfall-1", scene_type: "event" },
    };

    const { result } = renderHook(
      () => useStrategyEvent("pt-1", worldAwaiting),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.eventPackage).not.toBeNull();
    });

    expect(result.current.eventPackage?.title).toBe("Trouble: Treasury Shortfall");
    expect(result.current.eventPackage?.choices).toHaveLength(2);
    expect(result.current.eventPackage?.choices[0].id).toBe("shortfall_take_loan");
  });

  it("resolves a shortfall through the simulation's choice route with an operation guard", async () => {
    const worldAwaiting: CampaignWorldView = {
      ...mockWorld,
      status: "awaiting_scene",
      scene_id: "scene-shortfall-1",
      pending_scene: { scene_id: "scene-shortfall-1", scene_type: "event" },
    };

    mockedClient.post.mockResolvedValueOnce({ data: { success: true } });

    const onResolved = vi.fn();
    const { result } = renderHook(
      () => useStrategyEvent("pt-1", worldAwaiting, onResolved),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.eventPackage).not.toBeNull();
    });

    await act(async () => {
      await result.current.resolveChoice("shortfall_take_loan");
    });

    expect(mockedClient.post).toHaveBeenCalledWith(
      "/simulation/v1/playthroughs/pt-1/scenes/scene-shortfall-1/choice",
      expect.objectContaining({
        choice: "shortfall_take_loan",
        expected_world_version: 1,
        expected_turn: 3,
        operation_id: expect.any(String),
      }),
      { baseURL: "" }
    );
    expect(onResolved).toHaveBeenCalledTimes(1);
  });

  it("ignores a choice that is not a shortfall outcome", async () => {
    const worldAwaiting: CampaignWorldView = {
      ...mockWorld,
      status: "awaiting_scene",
      scene_id: "scene-shortfall-1",
      pending_scene: { scene_id: "scene-shortfall-1", scene_type: "event" },
    };
    const { result } = renderHook(() => useStrategyEvent("pt-1", worldAwaiting), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.eventPackage).not.toBeNull());
    await act(async () => {
      await result.current.resolveChoice("opt-1");
    });
    expect(mockedClient.post).not.toHaveBeenCalled();
  });

  it("does not invent a dialog for a negotiation scene", () => {
    const negotiating: CampaignWorldView = {
      ...mockWorld,
      status: "awaiting_scene",
      scene_id: "scene-talks-1",
      pending_scene: { scene_id: "scene-talks-1", scene_type: "negotiation" },
    };
    const { result } = renderHook(() => useStrategyEvent("pt-1", negotiating), {
      wrapper: createWrapper(),
    });
    expect(result.current.eventPackage).toBeNull();
  });

  it("does not guess a shortfall from an empty treasury when the scene cannot be loaded", async () => {
    const unknownScene: CampaignWorldView = {
      ...mockWorld,
      status: "awaiting_scene",
      scene_id: "scene-x",
      my_faction: { ...mockWorld.my_faction, treasury: 0 },
    };
    mockedClient.get.mockRejectedValueOnce(new Error("Not found"));
    const { result } = renderHook(() => useStrategyEvent("pt-1", unknownScene), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(mockedClient.get).toHaveBeenCalled());
    expect(result.current.eventPackage).toBeNull();
  });
});
