import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { usePlaytestStore } from "../stores/playtest.store";
import { usePlaytestTurns } from "./usePlaytestTurns";

interface StreamOptions {
  onTurnComplete: (turn: { actionText: string; narration: string }) => void;
}

const mocks = vi.hoisted(() => ({
  getPlaythrough: vi.fn(),
  streamOptions: { current: null as StreamOptions | null },
}));

vi.mock("@/shared/api/playthroughs.api", () => ({ getPlaythrough: mocks.getPlaythrough }));
vi.mock("@/shared/hooks/useTurnStream", () => ({
  useTurnStream: (options: StreamOptions) => {
    mocks.streamOptions.current = options;
    return {
      submitTurn: vi.fn(),
      cancelTurn: vi.fn(),
      narration: "",
      isStreaming: false,
      notice: null,
      failureMessage: null,
    };
  },
}));

const session = (playthroughId: string) => ({
  scenarioId: "s1",
  playthroughId,
  participantId: "p1",
  openingText: "",
  startedStamp: null,
  setupValues: {},
  state: {},
  note: null,
});

describe("usePlaytestTurns", () => {
  beforeEach(() => {
    usePlaytestStore.getState().endSession();
    mocks.getPlaythrough.mockReset();
  });

  it("ignores a state refresh that finishes after a new playtest has started", async () => {
    let resolveOld: (value: { state: Record<string, unknown> }) => void = () => undefined;
    mocks.getPlaythrough.mockReturnValue(
      new Promise((resolve) => {
        resolveOld = resolve;
      }),
    );
    usePlaytestStore.getState().beginSession(session("old"));
    renderHook(() => usePlaytestTurns());

    act(() => mocks.streamOptions.current?.onTurnComplete({ actionText: "a", narration: "b" }));
    act(() => usePlaytestStore.getState().beginSession({ ...session("new"), state: { fresh: true } }));
    await act(async () => resolveOld({ state: { stale: true } }));

    expect(usePlaytestStore.getState().state).toEqual({ fresh: true });
  });

  it("applies the refreshed state while the same playtest is still running", async () => {
    mocks.getPlaythrough.mockResolvedValue({ state: { hp: 3 } });
    usePlaytestStore.getState().beginSession(session("same"));
    renderHook(() => usePlaytestTurns());

    await act(async () => mocks.streamOptions.current?.onTurnComplete({ actionText: "a", narration: "b" }));

    expect(usePlaytestStore.getState().state).toEqual({ hp: 3 });
  });
});
