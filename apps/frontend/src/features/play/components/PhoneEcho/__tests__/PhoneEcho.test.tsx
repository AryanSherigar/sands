import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { usePlayStore } from "../../../stores/play.store";
import { PhoneEcho } from "../PhoneEcho";

const mic = vi.hoisted(() => ({
  isSupported: true,
  startError: null as Error | null,
  clip: new Blob(["voice"]),
}));
const player = vi.hoisted(() => ({
  played: [] as string[],
}));

vi.mock("@/shared/lib/audio/mic-recorder", () => {
  class MicRecorderError extends Error {
    constructor(
      public reason: string,
      message: string,
    ) {
      super(message);
    }
  }
  class MicRecorder {
    async start(): Promise<void> {
      if (mic.startError) throw mic.startError;
    }
    async stop(): Promise<Blob> {
      return mic.clip;
    }
    cancel(): void {}
  }
  return { MicRecorder, MicRecorderError, isVoiceInputSupported: () => mic.isSupported };
});

vi.mock("@/shared/lib/audio/phone-echo-player", () => ({
  playEcho: async () => {
    player.played.push("echo");
  },
  playBreathing: async (durationMs: number) => {
    player.played.push("breathing");
    await new Promise((resolve) => setTimeout(resolve, durationMs));
  },
}));

const EFFECT = {
  kind: "phone_echo" as const,
  params: { record_ms: 2000, delay_ms: 1000 },
};

const run = async (ms: number): Promise<void> => {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
};

describe("PhoneEcho", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mic.isSupported = true;
    mic.startError = null;
    player.played = [];
    useReaderPreferencesStore.setState({ reduceSensoryEffects: false });
    usePlayStore.setState({ active_client_effect: null, queued_client_effects: [] });
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("asks the player to speak, then plays their voice back", async () => {
    render(<PhoneEcho />);
    await act(async () => {
      usePlayStore.setState({ active_client_effect: EFFECT });
    });
    expect(screen.getByText("Say something.")).toBeInTheDocument();
    await run(2000 + 1000);
    expect(player.played).toEqual(["echo"]);
    expect(usePlayStore.getState().active_client_effect).toBeNull();
  });

  it("falls back to breathing without a microphone", async () => {
    mic.isSupported = false;
    render(<PhoneEcho />);
    await act(async () => {
      usePlayStore.setState({ active_client_effect: EFFECT });
    });
    expect(screen.getByText("Say something.")).toBeInTheDocument();
    await run(2000);
    expect(player.played).toEqual(["breathing"]);
    expect(usePlayStore.getState().active_client_effect).toBeNull();
  });

  it("falls back to breathing when the microphone is refused", async () => {
    mic.startError = new Error("permission-denied");
    render(<PhoneEcho />);
    await act(async () => {
      usePlayStore.setState({ active_client_effect: EFFECT });
    });
    await run(2000);
    expect(player.played).toEqual(["breathing"]);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("goes straight to breathing when effects are reduced", async () => {
    useReaderPreferencesStore.setState({ reduceSensoryEffects: true });
    render(<PhoneEcho />);
    await act(async () => {
      usePlayStore.setState({ active_client_effect: EFFECT });
    });
    await run(2000);
    expect(player.played).toEqual(["breathing"]);
  });

  it("renders nothing for other effects", () => {
    usePlayStore.setState({
      active_client_effect: {
        kind: "input_takeover",
        params: { text: "x", lock_ms: 1000, type_ms_per_char: 50 },
      },
    });
    render(<PhoneEcho />);
    expect(screen.queryByText("Say something.")).toBeNull();
  });
});
