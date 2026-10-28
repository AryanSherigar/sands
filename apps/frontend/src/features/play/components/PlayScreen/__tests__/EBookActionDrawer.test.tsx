import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { EBookActionDrawer } from "../EBook/EBookActionDrawer";
import { useVoiceInput } from "../../../hooks/useVoiceInput";

vi.mock("@/shared/hooks/useIsAlphaMode", () => ({
  useIsAlphaMode: () => false,
}));

vi.mock("../../../hooks/useVoiceInput");
const mockUseVoiceInput = vi.mocked(useVoiceInput);

function mockVoiceInput(
  overrides: Partial<ReturnType<typeof useVoiceInput>> = {},
) {
  mockUseVoiceInput.mockReturnValue({
    status: "idle",
    isSupported: false,
    errorMessage: null,
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
    cancelRecording: vi.fn(),
    ...overrides,
  });
}

describe("EBookActionDrawer", () => {
  beforeEach(() => {
    mockVoiceInput();
  });

  it("renders when open and submits action text", () => {
    const handleSubmit = vi.fn();

    render(
      <EBookActionDrawer onContinue={vi.fn()} onRetry={vi.fn()} canRetry={false} 
        onSubmit={handleSubmit}
        isNarrating={false}
      />,
    );

    const textarea = screen.getByPlaceholderText(/Action/i);
    fireEvent.change(textarea, {
      target: { value: "I inspect the ancient altar." },
    });

    const submitButton = screen.getByRole("button", { name: /Submit/i });
    fireEvent.click(submitButton);

    expect(handleSubmit).toHaveBeenCalledWith("I inspect the ancient altar.");
  });

  it("submits on Cmd+Enter shortcut", () => {
    const handleSubmit = vi.fn();

    render(
      <EBookActionDrawer onContinue={vi.fn()} onRetry={vi.fn()} canRetry={false} 
        onSubmit={handleSubmit}
        isNarrating={false}
      />,
    );

    const textarea = screen.getByPlaceholderText(/Action/i);
    fireEvent.change(textarea, { target: { value: "I light a torch." } });
    fireEvent.keyDown(textarea, { key: "Enter", metaKey: true });

    expect(handleSubmit).toHaveBeenCalledWith("I light a torch.");
  });

  it("offers only Do, Say and Continue, defaulting to Do", () => {
    render(
      <EBookActionDrawer
        onContinue={vi.fn()}
        onRetry={vi.fn()}
        canRetry={false}
        onSubmit={vi.fn()}
        isNarrating={false}
      />,
    );

    expect(screen.getByRole("button", { name: "Do" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Say" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Story" })).toBeNull();
    expect(screen.queryByRole("button", { name: "See" })).toBeNull();
    expect(screen.getByPlaceholderText(/Action \(Do\)/i)).toBeInTheDocument();
  });

  it("Continue mode disables the textbox and Submit continues the scene", () => {
    const handleContinue = vi.fn();
    const handleSubmit = vi.fn();
    render(
      <EBookActionDrawer
        onContinue={handleContinue}
        onRetry={vi.fn()}
        canRetry={false}
        onSubmit={handleSubmit}
        isNarrating={false}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.getByRole("textbox")).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /Submit/i }));

    expect(handleContinue).toHaveBeenCalledTimes(1);
    expect(handleSubmit).not.toHaveBeenCalled();
    expect(screen.getByPlaceholderText(/Action \(Do\)/i)).toBeInTheDocument();
  });

  it("shows Retry only when a retry is possible and calls onRetry", () => {
    const handleRetry = vi.fn();
    render(
      <EBookActionDrawer
        onContinue={vi.fn()}
        onRetry={handleRetry}
        canRetry={true}
        onSubmit={vi.fn()}
        isNarrating={false}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Retry/i }));
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });

  it("renders no chip row when actionChips is omitted", () => {
    render(
      <EBookActionDrawer onContinue={vi.fn()} onRetry={vi.fn()} canRetry={false} 
        onSubmit={vi.fn()}
        isNarrating={false}
      />,
    );

    expect(
      screen.queryByRole("button", { name: /explore/i }),
    ).not.toBeInTheDocument();
  });

  it("clicking a chip inserts its text into the textarea", () => {
    render(
      <EBookActionDrawer onContinue={vi.fn()} onRetry={vi.fn()} canRetry={false} 
        onSubmit={vi.fn()}
        isNarrating={false}
        actionChips={["I explore the ancient ruins."]}
      />,
    );

    const chipButton = screen.getByRole("button", {
      name: "I explore the ancient ruins.",
    });
    fireEvent.click(chipButton);

    const textarea = screen.getByPlaceholderText(/Action/i);
    expect(textarea).toHaveValue("I explore the ancient ruins.");
  });

  it("does not render a mic button when voice input is unsupported", () => {
    mockVoiceInput({ isSupported: false });
    render(
      <EBookActionDrawer onContinue={vi.fn()} onRetry={vi.fn()} canRetry={false} 
        onSubmit={vi.fn()}
        isNarrating={false}
      />,
    );

    expect(
      screen.queryByTitle(/Speak your action/i),
    ).not.toBeInTheDocument();
  });

  it("clicking the mic button when idle starts recording", () => {
    const startRecording = vi.fn();
    mockVoiceInput({ isSupported: true, status: "idle", startRecording });
    render(
      <EBookActionDrawer onContinue={vi.fn()} onRetry={vi.fn()} canRetry={false} 
        onSubmit={vi.fn()}
        isNarrating={false}
      />,
    );

    fireEvent.click(screen.getByTitle(/Speak your action/i));
    expect(startRecording).toHaveBeenCalledTimes(1);
  });

  it("clicking the mic button while recording stops recording", () => {
    const stopRecording = vi.fn();
    mockVoiceInput({ isSupported: true, status: "recording", stopRecording });
    render(
      <EBookActionDrawer onContinue={vi.fn()} onRetry={vi.fn()} canRetry={false} 
        onSubmit={vi.fn()}
        isNarrating={false}
      />,
    );

    fireEvent.click(screen.getByTitle(/Stop recording/i));
    expect(stopRecording).toHaveBeenCalledTimes(1);
  });

  it("populates the textarea from a transcript without auto-submitting", () => {
    const handleSubmit = vi.fn();
    let capturedOnTranscribed: (text: string) => void = () => {};
    mockUseVoiceInput.mockImplementation((onTranscribed) => {
      capturedOnTranscribed = onTranscribed;
      return {
        status: "idle",
        isSupported: true,
        errorMessage: null,
        startRecording: vi.fn(),
        stopRecording: vi.fn(),
        cancelRecording: vi.fn(),
      };
    });

    render(
      <EBookActionDrawer onContinue={vi.fn()} onRetry={vi.fn()} canRetry={false} 
        onSubmit={handleSubmit}
        isNarrating={false}
      />,
    );

    act(() => {
      capturedOnTranscribed("I search the room for traps.");
    });

    const textarea = screen.getByPlaceholderText(/Action/i);
    expect(textarea).toHaveValue("I search the room for traps.");
    expect(handleSubmit).not.toHaveBeenCalled();
  });

  it("renders the voice error message in place of the mode prefix", () => {
    mockVoiceInput({
      isSupported: true,
      status: "error",
      errorMessage: "Microphone access was denied — enable it in your browser settings.",
    });
    render(
      <EBookActionDrawer onContinue={vi.fn()} onRetry={vi.fn()} canRetry={false} 
        onSubmit={vi.fn()}
        isNarrating={false}
      />,
    );

    expect(
      screen.getByText(/Microphone access was denied/i),
    ).toBeInTheDocument();
  });
});
