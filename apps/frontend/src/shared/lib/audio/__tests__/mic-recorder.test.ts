import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  MicRecorder,
  MicRecorderError,
  isVoiceInputSupported,
} from "../mic-recorder";

class FakeMediaRecorder {
  static isTypeSupported = vi.fn(() => true);
  ondataavailable: ((e: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  mimeType: string;
  state: "recording" | "inactive" = "inactive";

  constructor(
    public stream: MediaStream,
    options: { mimeType: string },
  ) {
    this.mimeType = options.mimeType;
  }

  start() {
    this.state = "recording";
  }

  stop() {
    this.state = "inactive";
    this.ondataavailable?.({ data: new Blob(["chunk"]) });
    this.onstop?.();
  }
}

function fakeStream(): MediaStream {
  const track = { stop: vi.fn() };
  return { getTracks: () => [track] } as unknown as MediaStream;
}

describe("isVoiceInputSupported", () => {
  const originalMediaRecorder = globalThis.MediaRecorder;

  afterEach(() => {
    globalThis.MediaRecorder = originalMediaRecorder;
  });

  it("returns false when MediaRecorder is undefined", () => {
    // @ts-expect-error simulating a browser without MediaRecorder
    delete globalThis.MediaRecorder;
    expect(isVoiceInputSupported()).toBe(false);
  });

  it("returns false when getUserMedia is unavailable", () => {
    globalThis.MediaRecorder = FakeMediaRecorder as unknown as typeof MediaRecorder;
    const original = navigator.mediaDevices;
    // @ts-expect-error simulating a browser without getUserMedia
    delete navigator.mediaDevices;
    expect(isVoiceInputSupported()).toBe(false);
    Object.defineProperty(navigator, "mediaDevices", {
      value: original,
      configurable: true,
    });
  });
});

describe("MicRecorder", () => {
  beforeEach(() => {
    globalThis.MediaRecorder = FakeMediaRecorder as unknown as typeof MediaRecorder;
    Object.defineProperty(navigator, "mediaDevices", {
      value: { getUserMedia: vi.fn() },
      configurable: true,
    });
  });

  it("throws permission-denied when getUserMedia rejects with NotAllowedError", async () => {
    vi.mocked(navigator.mediaDevices.getUserMedia).mockRejectedValue(
      new DOMException("denied", "NotAllowedError"),
    );

    const recorder = new MicRecorder();
    await expect(recorder.start()).rejects.toMatchObject({
      reason: "permission-denied",
    } satisfies Partial<MicRecorderError>);
  });

  it("resolves stop() with a Blob assembled from recorded chunks", async () => {
    vi.mocked(navigator.mediaDevices.getUserMedia).mockResolvedValue(fakeStream());

    const recorder = new MicRecorder();
    await recorder.start();
    const blob = await recorder.stop();

    expect(blob).toBeInstanceOf(Blob);
  });

  it("requests mono audio with browser noise processing enabled", async () => {
    vi.mocked(navigator.mediaDevices.getUserMedia).mockResolvedValue(fakeStream());

    await new MicRecorder().start();

    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
  });

  it("stops all tracks on the stream when cancelled", async () => {
    const stream = fakeStream();
    vi.mocked(navigator.mediaDevices.getUserMedia).mockResolvedValue(stream);

    const recorder = new MicRecorder();
    await recorder.start();
    recorder.cancel();

    expect(stream.getTracks()[0].stop).toHaveBeenCalledTimes(1);
  });
});
