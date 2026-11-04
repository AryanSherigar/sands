import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { UseVoiceInputResult } from "../../../../hooks/useVoiceInput";
import { useVoiceInput } from "../../../../hooks/useVoiceInput";
import { SpeechTalkInput } from "../SpeechTalkInput";

vi.mock("../../../../hooks/useVoiceInput");

const startRecording = vi.fn(() => Promise.resolve());
const stopRecording = vi.fn(() => Promise.resolve());

function mockVoice(overrides: Partial<UseVoiceInputResult> = {}): void {
  vi.mocked(useVoiceInput).mockReturnValue({
    status: "idle",
    isSupported: true,
    errorMessage: null,
    startRecording,
    stopRecording,
    cancelRecording: vi.fn(),
    ...overrides,
  });
}

const renderInput = (onSubmit = vi.fn()) => {
  render(
    <SpeechTalkInput playthroughId="pt-1" talkLabel="Opening talk" isSubmitting={false} onSubmit={onSubmit} />,
  );
  return onSubmit;
};

describe("SpeechTalkInput", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockVoice();
  });

  it("records while the speak button is held and stops when it is released", async () => {
    const user = userEvent.setup();
    renderInput();
    const button = screen.getByRole("button", { name: /hold to speak/i });
    await user.pointer({ keys: "[MouseLeft>]", target: button });
    expect(startRecording).toHaveBeenCalledTimes(1);
    expect(stopRecording).not.toHaveBeenCalled();
    await user.pointer({ keys: "[/MouseLeft]", target: button });
    expect(stopRecording).toHaveBeenCalledTimes(1);
  });

  it("stops recording if the pointer slides off the button before release", async () => {
    const user = userEvent.setup();
    renderInput();
    const button = screen.getByRole("button", { name: /hold to speak/i });
    await user.pointer({ keys: "[MouseLeft>]", target: button });
    await user.pointer({ target: document.body });
    expect(stopRecording).toHaveBeenCalledTimes(1);
  });

  it("stops recording if the browser cancels the press", async () => {
    const user = userEvent.setup();
    renderInput();
    const button = screen.getByRole("button", { name: /hold to speak/i });
    await user.pointer({ keys: "[MouseLeft>]", target: button });
    fireEvent.pointerCancel(button);
    expect(stopRecording).toHaveBeenCalledTimes(1);
  });

  it("puts the transcript in the box so the player can fix it before delivering", async () => {
    const onSubmit = renderInput();
    const onTranscribed = vi.mocked(useVoiceInput).mock.calls[0]?.[0];
    expect(onTranscribed).toBeDefined();
    await vi.waitFor(() => onTranscribed?.("we march at dawn"));
    const box = await screen.findByRole("textbox", { name: /your talk/i });
    await vi.waitFor(() => expect(box).toHaveValue("we march at dawn"));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("shows a microphone problem and still lets the player type and deliver", async () => {
    mockVoice({ status: "error", errorMessage: "Microphone access was denied — enable it in your browser settings." });
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(
      <SpeechTalkInput playthroughId="pt-1" talkLabel="Opening talk" isSubmitting={false} onSubmit={onSubmit} />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/microphone access was denied/i);
    await user.type(screen.getByRole("textbox", { name: /your talk/i }), "Hold the line.");
    expect(screen.getByRole("button", { name: /^deliver/i })).toBeDisabled();
  });

  it("delivers the trimmed text and clears the box", async () => {
    const user = userEvent.setup();
    const onSubmit = renderInput();
    await user.type(screen.getByRole("textbox", { name: /your talk/i }), "  Stand fast.  ");
    await user.click(screen.getByRole("button", { name: /^deliver/i }));
    expect(onSubmit).toHaveBeenCalledWith("Stand fast.");
    expect(screen.getByRole("textbox", { name: /your talk/i })).toHaveValue("");
  });
});
