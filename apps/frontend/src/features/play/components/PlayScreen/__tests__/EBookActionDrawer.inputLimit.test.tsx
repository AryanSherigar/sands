import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { EBookActionDrawer } from "../EBook/EBookActionDrawer";
import { useVoiceInput } from "../../../hooks/useVoiceInput";
import { TURN_ACTION_MAX_CHARS } from "../../../constants/turnInput.constants";

vi.mock("@/shared/hooks/useIsAlphaMode", () => ({
  useIsAlphaMode: () => false,
}));

vi.mock("../../../hooks/useVoiceInput");
const mockUseVoiceInput = vi.mocked(useVoiceInput);

let deliverTranscript: (transcript: string) => void = () => {};

function renderDrawer() {
  return render(
    <EBookActionDrawer onContinue={vi.fn()} onRetry={vi.fn()} canRetry={false} 
      onSubmit={vi.fn()}
      isNarrating={false}
    />,
  );
}

describe("EBookActionDrawer — action size cap", () => {
  beforeEach(() => {
    mockUseVoiceInput.mockImplementation((onTranscribed) => {
      deliverTranscript = onTranscribed;
      return {
        status: "idle",
        isSupported: false,
        errorMessage: null,
        startRecording: vi.fn(),
        stopRecording: vi.fn(),
        cancelRecording: vi.fn(),
      };
    });
  });

  it("limits the textarea to the action cap", () => {
    renderDrawer();

    expect(screen.getByPlaceholderText(/Action/i)).toHaveAttribute(
      "maxLength",
      String(TURN_ACTION_MAX_CHARS),
    );
  });

  it("hides the counter for short text", () => {
    renderDrawer();

    fireEvent.change(screen.getByPlaceholderText(/Action/i), {
      target: { value: "I look around." },
    });

    expect(screen.queryByText(/\/2000/)).not.toBeInTheDocument();
  });

  it("shows the counter as the text nears the cap", () => {
    renderDrawer();

    fireEvent.change(screen.getByPlaceholderText(/Action/i), {
      target: { value: "a".repeat(1700) },
    });

    expect(screen.getByText("1700/2000")).toBeInTheDocument();
  });

  it("warns when a voice transcript pushes the text past the cap", () => {
    renderDrawer();

    act(() => deliverTranscript("a".repeat(TURN_ACTION_MAX_CHARS + 100)));

    expect(
      screen.getByText(/2100\/2000 - extra text will be cut/),
    ).toBeInTheDocument();
  });
});
