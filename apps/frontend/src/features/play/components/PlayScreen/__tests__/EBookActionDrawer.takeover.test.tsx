import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { useVoiceInput } from "../../../hooks/useVoiceInput";
import { usePlayStore } from "../../../stores/play.store";
import { EBookActionDrawer } from "../EBook/EBookActionDrawer";

vi.mock("@/shared/hooks/useIsAlphaMode", () => ({
  useIsAlphaMode: () => false,
}));

vi.mock("../../../hooks/useVoiceInput");

const LINE = "Get me out of here, Orr";

const advance = (ms: number): void => {
  act(() => {
    vi.advanceTimersByTime(ms);
  });
};

describe("EBookActionDrawer input takeover", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(useVoiceInput).mockReturnValue({
      status: "idle",
      isSupported: false,
      errorMessage: null,
      startRecording: vi.fn(),
      stopRecording: vi.fn(),
      cancelRecording: vi.fn(),
    });
    useReaderPreferencesStore.setState({ reduceSensoryEffects: false });
    usePlayStore.setState({ active_client_effect: null, queued_client_effects: [] });
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("locks the input, shows the line, then restores the draft", () => {
    render(
      <EBookActionDrawer onContinue={vi.fn()} onRetry={vi.fn()} canRetry={false}  onSubmit={vi.fn()} isNarrating={false} />,
    );
    const textarea = screen.getByLabelText(/Action/i) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "I sign" } });

    act(() => {
      usePlayStore.setState({
        active_client_effect: {
          kind: "input_takeover",
          params: { text: LINE, lock_ms: 4500, type_ms_per_char: 50 },
        },
      });
    });
    advance(50 * LINE.length);

    expect(textarea.value).toBe("");
    expect(textarea.disabled).toBe(true);
    expect(textarea.placeholder).toBe(LINE);

    advance(4500);

    expect(textarea.value).toBe("I sign");
    expect(textarea.disabled).toBe(false);
  });
});
