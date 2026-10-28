import { beforeEach, describe, expect, it, vi } from "vitest";
import { usePlayStore } from "../play.store";
import type { PlaythroughData } from "../../types/play.types";
import type { SSEHandlers } from "@/shared/lib/sse-client";
import { emitAlphaEvent } from "@/shared/lib/alpha-events";

let capturedHandlers: SSEHandlers | null = null;

vi.mock("@/shared/lib/sse-client", () => ({
  createPostSSEConnection: (
    _url: string,
    _body: unknown,
    _token: string | null,
    handlers: SSEHandlers,
  ) => {
    capturedHandlers = handlers;
    return vi.fn();
  },
}));

vi.mock("@/shared/lib/alpha-events", () => ({
  emitAlphaEvent: vi.fn(),
}));

vi.mock("@/shared/api/playthroughs.api", () => ({ getPlaythrough: vi.fn() }));

function emittedNames(): string[] {
  return vi.mocked(emitAlphaEvent).mock.calls.map((call) => call[0]);
}

function emittedProps(name: string): Record<string, unknown> {
  const call = vi.mocked(emitAlphaEvent).mock.calls.find((c) => c[0] === name);
  return (call?.[1] ?? {}) as Record<string, unknown>;
}

describe("play.store alpha telemetry", () => {
  beforeEach(() => {
    capturedHandlers = null;
    vi.mocked(emitAlphaEvent).mockClear();
    usePlayStore.setState({
      playthrough: {
        playthrough_id: "pt-1",
        mode: "master",
        turns: [],
        is_spectator: false,
        participant_id: "participant-1",
        can_act: true,
      } as unknown as PlaythroughData,
      last_submitted_action: "",
      last_client_action_id: null,
      last_check_report: null,
      is_narrating: false,
    });
  });

  it("reports perceived latency when a turn finishes", () => {
    usePlayStore.getState().submitTurn("I open the door.");
    capturedHandlers!.onEvent("narration", "It creaks.");

    capturedHandlers!.onEvent("done", "");

    expect(emittedProps("turn_perceived_latency")).toMatchObject({
      turn_number: 1,
    });
    expect(emittedProps("turn_perceived_latency").first_token_ms).not.toBeNull();
  });

  it("reports a stall when the connection drops", () => {
    usePlayStore.getState().submitTurn("I open the door.");

    capturedHandlers!.onError?.(new Error("connection lost"));

    expect(emittedNames()).toContain("stream_stall");
  });

  it("reports a stall when the stream closes without finishing", () => {
    usePlayStore.getState().submitTurn("I open the door.");

    capturedHandlers!.onClose?.();

    expect(emittedNames()).toContain("stream_stall");
  });

  it("emits one turn_retry per click, after an error, with the same action id", () => {
    usePlayStore.getState().submitTurn("I open the door.");
    const actionId = usePlayStore.getState().last_client_action_id;
    capturedHandlers!.onError?.(new Error("connection lost"));
    vi.mocked(emitAlphaEvent).mockClear();

    usePlayStore.getState().retryLastTurn();

    const retries = vi
      .mocked(emitAlphaEvent)
      .mock.calls.filter((call) => call[0] === "turn_retry");
    expect(retries).toHaveLength(1);
    expect(retries[0][1]).toEqual({
      kind: "after_error",
      turn_number: 1,
      client_action_id: actionId,
    });
    expect(emittedNames()).toContain("stream_reconnect");
  });

  it("emits a check_report_resend retry when a report is waiting", () => {
    usePlayStore.setState({
      last_check_report: {
        report: { check_id: "chk-1", choice_id: "answer" },
        label: "Answer it",
      },
      last_client_action_id: "action-9",
    });

    usePlayStore.getState().retryLastTurn();

    expect(emittedProps("turn_retry")).toMatchObject({
      kind: "check_report_resend",
      client_action_id: "action-9",
    });
  });

  it("emits nothing and sends nothing when no recovery is possible", () => {
    usePlayStore.getState().retryLastTurn();

    expect(emittedNames()).toEqual([]);
  });
});
