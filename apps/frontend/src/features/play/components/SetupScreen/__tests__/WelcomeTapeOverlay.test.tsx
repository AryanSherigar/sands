import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { server } from "@/test/msw/server";
import { usePlayStore } from "../../../stores/play.store";
import { WelcomeTapeOverlay } from "../WelcomeTapeOverlay";

class TapeAudioContext {
  static latest: TapeAudioContext;
  constructor() { TapeAudioContext.latest = this; }
  static hasAutoplayBlocked = false;
  static closedCount = 0;
  currentTime = 0;
  state = "suspended";
  destination = {};
  createGain() { return { gain: { value: 1 }, connect: vi.fn() }; }
  createAnalyser() { return { connect: vi.fn(), fftSize: 32, getFloatTimeDomainData: vi.fn() }; }
  createBufferSource() { return { connect: vi.fn(), start: vi.fn(), stop: vi.fn() }; }
  async decodeAudioData() { return { duration: 1 }; }
  async resume() { if (TapeAudioContext.hasAutoplayBlocked) throw new Error("Autoplay blocked"); this.state = "running"; }
  async close() { this.state = "closed"; TapeAudioContext.closedCount += 1; }
}

function renderTape(playthroughId: string | null = "run-1") {
  const handleComplete = vi.fn();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const view = render(<QueryClientProvider client={client}><WelcomeTapeOverlay playthroughId={playthroughId} characterName="Alex" onComplete={handleComplete} /></QueryClientProvider>);
  return { ...view, handleComplete };
}

beforeEach(() => {
  TapeAudioContext.closedCount = 0; TapeAudioContext.hasAutoplayBlocked = false;
  vi.stubGlobal("AudioContext", TapeAudioContext);
  URL.createObjectURL = vi.fn(() => "blob:tape"); URL.revokeObjectURL = vi.fn();
  vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => undefined);
  useReaderPreferencesStore.setState({ reduceSensoryEffects: false });
  usePlayStore.setState({ is_audio_muted: false });
  server.use(http.get("*/welcome-tapes/tallis-v1/*", () => new HttpResponse(new Uint8Array([1, 2, 3]))));
});

afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("welcome tape", () => {
  it("shows static immediately and allows skipping before creation", async () => {
    const user = userEvent.setup();
    const view = renderTape(null);
    expect(screen.getByRole("status")).toHaveTextContent("ACQUIRING SIGNAL");
    await user.click(screen.getByRole("button", { name: "Skip tape" }));
    expect(view.handleComplete).toHaveBeenCalledOnce();
    view.unmount();
    expect(TapeAudioContext.closedCount).toBeGreaterThan(0);
  });

  it("uses the generic closing when the provider fails and exposes controls", async () => {
    server.use(http.post("http://localhost:8001/v1/voice/welcome/run-1", () => new HttpResponse(null, { status: 502 })));
    const user = userEvent.setup(); renderTape();
    await waitFor(() => expect(screen.getByRole("button", { name: "Pause" })).toBeVisible());
    await user.click(screen.getByRole("button", { name: "Pause" }));
    expect(screen.getByRole("button", { name: "Play tape" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Captions" }));
    expect(screen.getByRole("button", { name: "Captions" })).toHaveAttribute("aria-pressed", "false");
  });

  it("offers a user gesture after autoplay is blocked", async () => {
    TapeAudioContext.hasAutoplayBlocked = true;
    server.use(http.post("http://localhost:8001/v1/voice/welcome/run-1", () => new HttpResponse(new Uint8Array([1]))));
    renderTape();
    await waitFor(() => expect(screen.getByRole("button", { name: "Play tape" })).toBeVisible());
    TapeAudioContext.hasAutoplayBlocked = false;
    await userEvent.click(screen.getByRole("button", { name: "Play tape" }));
    expect(screen.getByRole("button", { name: "Pause" })).toBeVisible();
  });

  it("offers Continue when fixed media exceeds its deadline", async () => {
    vi.useFakeTimers();
    server.use(http.get("*/welcome-tapes/tallis-v1/*", async () => {
      await new Promise(resolve => setTimeout(resolve, 60000));
      return new HttpResponse(new Uint8Array([1]));
    }));
    renderTape(null);
    await act(async () => { await vi.advanceTimersByTimeAsync(21000); });
    expect(screen.getByRole("alert")).toHaveTextContent("Tape could not load");
    expect(screen.getByRole("button", { name: "Continue to story" })).toBeVisible();
  });

  it("retries failed fixed media", async () => {
    server.use(http.get("*/welcome-tapes/tallis-v1/*", () => new HttpResponse(null, { status: 503 })));
    const user = userEvent.setup(); renderTape();
    expect(await screen.findByRole("alert")).toHaveTextContent("Tape could not load");
    server.use(http.get("*/welcome-tapes/tallis-v1/*", () => new HttpResponse(new Uint8Array([1]))),
      http.post("http://localhost:8001/v1/voice/welcome/run-1", () => new HttpResponse(null, { status: 502 })));
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("button", { name: "Pause" })).toBeVisible();
  });

  it("shows a still portrait when reduced motion is enabled", async () => {
    useReaderPreferencesStore.setState({ reduceSensoryEffects: true });
    usePlayStore.setState({ is_audio_muted: true });
    renderTape(null);
    expect(screen.getByAltText("Katie, Personnel Services")).toBeVisible();
    expect(screen.getByRole("button", { name: "Unmute" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Skip tape" })).toBeVisible();
  });

  it("plays the personalized closing then completes the hold and black tail", async () => {
    server.use(http.post("http://localhost:8001/v1/voice/welcome/run-1", () => new HttpResponse(new Uint8Array([1]))));
    const view = renderTape();
    await screen.findByRole("button", { name: "Pause" });
    TapeAudioContext.latest.currentTime = 45;
    expect(await screen.findByText("Thank you for your service, Alex.")).toBeVisible();
    expect(view.handleComplete).not.toHaveBeenCalled();
    TapeAudioContext.latest.currentTime = 49;
    await waitFor(() => expect(view.handleComplete).toHaveBeenCalledOnce());
  });

  it("falls back after the voice deadline", async () => {
    server.use(http.post("http://localhost:8001/v1/voice/welcome/run-1", async () => {
      await new Promise(resolve => setTimeout(resolve, 60000));
      return new HttpResponse(new Uint8Array([1]));
    }));
    renderTape();
    expect(await screen.findByRole("button", { name: "Pause" }, { timeout: 17000 })).toBeVisible();
  }, 20000);
});
