import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import {
  DEFAULT_COMPOSURE_CONFIG,
  type ComposureConfigShape,
} from "@/shared/types/minigame.types";
import { ComposureMinigame } from "../ComposureMinigame";
import { RESOLUTION_BEAT_MS } from "../composurePresets";
import { FakeComposureContext } from "./fakeComposureContext";

const FIRST_BEAT_MS = 1500;
const BEAT_GAP_MS = 1000;

const config: ComposureConfigShape = {
  ...DEFAULT_COMPOSURE_CONFIG,
  target_bpm: 60,
  beats_to_win: 3,
  max_strikes: 2,
  tolerance_ms: 180,
  keys: ["W"],
  texts: {
    instructions: "Hum to the beat.",
    start_text: "Begin",
    win_text: "You kept it together.",
    lose_text: "It found you.",
  },
};

let contexts: FakeComposureContext[] = [];
let frames: FrameRequestCallback[] = [];
let perfOffset = 0;

class StubAudioContext extends FakeComposureContext {
  constructor() {
    super();
    contexts.push(this);
  }
}

const runFrame = (): void => {
  const pending = frames;
  frames = [];
  act(() => pending.forEach((callback) => callback(0)));
};

const setAudioTime = (ms: number): void => {
  contexts[0].currentTime = ms / 1000;
};

const pressW = (clockMs: number): void => {
  const event = new KeyboardEvent("keydown", { code: "KeyW", cancelable: true });
  Object.defineProperty(event, "timeStamp", { value: perfOffset + clockMs });
  act(() => {
    window.dispatchEvent(event);
  });
};

const setHidden = (isHidden: boolean): void => {
  vi.spyOn(document, "hidden", "get").mockReturnValue(isHidden);
  act(() => {
    document.dispatchEvent(new Event("visibilitychange"));
  });
};

const begin = (): void => {
  fireEvent.click(screen.getByRole("button", { name: "Begin" }));
  perfOffset = performance.now();
};

const start = async (onComplete = vi.fn()) => {
  render(<ComposureMinigame composureConfig={config} onComplete={onComplete} />);
  begin();
  return onComplete;
};

describe("ComposureMinigame", () => {
  beforeEach(() => {
    contexts = [];
    frames = [];
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    vi.spyOn(Math, "random").mockReturnValue(0);
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => {
      frames.push(callback);
      return frames.length;
    });
    vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {});
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    window.AudioContext = StubAudioContext as unknown as typeof AudioContext;
    useReaderPreferencesStore.setState({ reduceSensoryEffects: false });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("shows the instructions and waits for a click before making any sound", () => {
    render(<ComposureMinigame composureConfig={config} onComplete={vi.fn()} />);

    expect(screen.getByText("Hum to the beat.")).toBeInTheDocument();
    expect(contexts).toHaveLength(0);
  });

  it("starts the audio clock on the Begin click", async () => {
    await start();

    expect(contexts).toHaveLength(1);
    expect(screen.queryByText("Hum to the beat.")).toBeNull();
  });

  it("lights a streak pip for a key pressed on the beat", async () => {
    await start();
    setAudioTime(FIRST_BEAT_MS);

    pressW(FIRST_BEAT_MS);

    expect(screen.getByLabelText("Streak 1 of 3")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Hit");
  });

  it("reports a win with the longest streak after the resolution beat", async () => {
    const onComplete = await start();
    for (let i = 0; i < 3; i += 1) {
      setAudioTime(FIRST_BEAT_MS + i * BEAT_GAP_MS);
      pressW(FIRST_BEAT_MS + i * BEAT_GAP_MS);
    }

    expect(screen.getByText("You kept it together.")).toBeInTheDocument();
    expect(onComplete).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(RESOLUTION_BEAT_MS);
    });

    expect(onComplete).toHaveBeenCalledWith({ outcome_tag: "win", score: 3 });
  });

  it("counts a missed beat as a strike and loses at max strikes", async () => {
    const onComplete = await start();

    setAudioTime(FIRST_BEAT_MS + 200);
    runFrame();
    expect(screen.getByLabelText("Strikes 1 of 2")).toBeInTheDocument();
    setAudioTime(FIRST_BEAT_MS + BEAT_GAP_MS + 200);
    runFrame();
    act(() => {
      vi.advanceTimersByTime(RESOLUTION_BEAT_MS);
    });

    expect(screen.getByText("It found you.")).toBeInTheDocument();
    expect(onComplete).toHaveBeenCalledWith({ outcome_tag: "lose", score: 0 });
  });

  it("pauses on a hidden tab and never counts that time as a strike", async () => {
    await start();
    setHidden(true);
    setAudioTime(FIRST_BEAT_MS + 10 * BEAT_GAP_MS);
    runFrame();

    expect(screen.getByText("Paused")).toBeInTheDocument();
    expect(screen.getByLabelText("Strikes 0 of 2")).toBeInTheDocument();
    expect(contexts[0].state).toBe("suspended");

    setHidden(false);
    expect(screen.queryByText("Paused")).toBeNull();
    expect(contexts[0].state).toBe("running");
  });

  it("shows a bordered Strike message instead of a flash with reduced effects", async () => {
    useReaderPreferencesStore.setState({ reduceSensoryEffects: true });
    await start();

    setAudioTime(FIRST_BEAT_MS + 300);
    runFrame();

    const message = screen.getByRole("status");
    expect(message).toHaveTextContent("Strike");
    expect(message).toHaveClass("border");
  });

  it("is more forgiving with reduced effects (window widened by half)", async () => {
    useReaderPreferencesStore.setState({ reduceSensoryEffects: true });
    await start();
    setAudioTime(FIRST_BEAT_MS + 250);

    pressW(FIRST_BEAT_MS + 250);

    expect(screen.getByLabelText("Streak 1 of 3")).toBeInTheDocument();
  });

  it("still runs when the browser has no AudioContext", async () => {
    // @ts-expect-error simulating a browser without Web Audio
    window.AudioContext = undefined;
    render(<ComposureMinigame composureConfig={config} onComplete={vi.fn()} />);

    begin();

    expect(screen.getByLabelText("Streak 0 of 3")).toBeInTheDocument();
  });
});
