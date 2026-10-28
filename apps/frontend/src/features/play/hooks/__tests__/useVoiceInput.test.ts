import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useVoiceInput } from "../useVoiceInput";
import { transcribeAudio } from "../../api/voice.api";
import {
  MicRecorder,
  MicRecorderError,
  isVoiceInputSupported,
} from "@/shared/lib/audio/mic-recorder";

vi.mock("../../api/voice.api");
vi.mock("@/shared/lib/audio/mic-recorder", async () => {
  const actual = await vi.importActual<
    typeof import("@/shared/lib/audio/mic-recorder")
  >("@/shared/lib/audio/mic-recorder");
  return {
    ...actual,
    isVoiceInputSupported: vi.fn(() => true),
    MicRecorder: vi.fn(),
  };
});

const mockTranscribeAudio = vi.mocked(transcribeAudio);
const MockMicRecorder = vi.mocked(MicRecorder);
const mockIsVoiceInputSupported = vi.mocked(isVoiceInputSupported);

function installFakeRecorder(overrides: {
  start?: () => Promise<void>;
  stop?: () => Promise<Blob>;
}) {
  MockMicRecorder.mockImplementation(function () {
    return {
      start: overrides.start ?? vi.fn().mockResolvedValue(undefined),
      stop: overrides.stop ?? vi.fn().mockResolvedValue(new Blob()),
      cancel: vi.fn(),
    } as unknown as MicRecorder;
  });
}

describe("useVoiceInput", () => {
  beforeEach(() => {
    mockIsVoiceInputSupported.mockReturnValue(true);
    installFakeRecorder({});
  });

  it("transitions idle -> recording on startRecording", async () => {
    const { result } = renderHook(() => useVoiceInput(vi.fn()));

    await act(async () => {
      await result.current.startRecording();
    });

    expect(result.current.status).toBe("recording");
  });

  it("passes the playthrough id to transcription so names can be biased", async () => {
    mockTranscribeAudio.mockResolvedValue("I greet Zhaerith");
    const { result } = renderHook(() => useVoiceInput(vi.fn(), "playthrough-1"));

    await act(async () => {
      await result.current.startRecording();
    });
    await act(async () => {
      await result.current.stopRecording();
    });

    expect(mockTranscribeAudio).toHaveBeenCalledWith(expect.any(Blob), "playthrough-1");
  });

  it("transitions recording -> transcribing -> idle and calls onTranscribed", async () => {
    mockTranscribeAudio.mockResolvedValue("I open the chest");
    const onTranscribed = vi.fn();
    const { result } = renderHook(() => useVoiceInput(onTranscribed));

    await act(async () => {
      await result.current.startRecording();
    });
    await act(async () => {
      await result.current.stopRecording();
    });

    expect(onTranscribed).toHaveBeenCalledWith("I open the chest");
    expect(result.current.status).toBe("idle");
  });

  it("transitions to error with a permission-denied message when start fails", async () => {
    installFakeRecorder({
      start: vi
        .fn()
        .mockRejectedValue(
          new MicRecorderError("permission-denied", "denied"),
        ),
    });
    const { result } = renderHook(() => useVoiceInput(vi.fn()));

    await act(async () => {
      await result.current.startRecording();
    });

    expect(result.current.status).toBe("error");
    expect(result.current.errorMessage).toMatch(/Microphone access was denied/i);
  });

  it("transitions to error and skips onTranscribed when transcription fails", async () => {
    mockTranscribeAudio.mockRejectedValue(new Error("network down"));
    const onTranscribed = vi.fn();
    const { result } = renderHook(() => useVoiceInput(onTranscribed));

    await act(async () => {
      await result.current.startRecording();
    });
    await act(async () => {
      await result.current.stopRecording();
    });

    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(onTranscribed).not.toHaveBeenCalled();
  });
});
