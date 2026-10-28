import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { useVoiceInput } from "../../../hooks/useVoiceInput";
import { INTRUSIVE_INTERVAL_MS } from "../../../hooks/useIntrusivePlaceholder";
import { usePlayStore } from "../../../stores/play.store";
import { PlaythroughData } from "../../../types/play.types";
import { EBookActionDrawer } from "../EBook/EBookActionDrawer";

vi.mock("@/shared/hooks/useIsAlphaMode", () => ({
  useIsAlphaMode: () => false,
}));

vi.mock("../../../hooks/useVoiceInput");

const setSanity = (sanity: number): void => {
  usePlayStore.setState({
    playthrough: {
      playthrough_id: "pt-1",
      enabled_tools: ["status_hud", "atmosphere"],
      hud_hints: {
        meters: [
          {
            path: "sanity",
            hint: {
              kind: "meter",
              label: "Sanity",
              clamp_min: 0,
              clamp_max: 100,
              effects: {
                intrusive_below: 50,
                intrusive_thoughts: ["don't turn around"],
              },
            },
          },
        ],
      },
      state: { sanity },
    } as unknown as PlaythroughData,
  });
};

const advance = (ms: number): void => {
  act(() => {
    vi.advanceTimersByTime(ms);
  });
};

// The drawer focuses its input 100 ms after opening, which restarts the
// alternation; React only applies that inside a separate act.
const advancePastOpeningFocus = (): void => advance(200);

const renderDrawer = () =>
  render(
    <EBookActionDrawer onContinue={vi.fn()} onRetry={vi.fn()} canRetry={false} 
      onSubmit={vi.fn()}
      isNarrating={false}
    />,
  );

describe("EBookActionDrawer intrusive placeholder", () => {
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
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("whispers an authored phrase while sanity is low, keeping an accessible name", () => {
    setSanity(20);
    renderDrawer();

    advancePastOpeningFocus();
    advance(INTRUSIVE_INTERVAL_MS);

    const textarea = screen.getByPlaceholderText("don't turn around");
    expect(textarea.className).toContain("placeholder:font-eerie");
    expect(screen.getByLabelText(/Action/i)).toBe(textarea);
  });

  it("goes back to the standard text on focus and whispers again later", () => {
    setSanity(20);
    renderDrawer();
    advancePastOpeningFocus();
    advance(INTRUSIVE_INTERVAL_MS);

    fireEvent.focus(screen.getByPlaceholderText("don't turn around"));

    expect(screen.getByPlaceholderText(/Action/i)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText("don't turn around")).toBeNull();
    advance(INTRUSIVE_INTERVAL_MS);
    expect(screen.getByPlaceholderText("don't turn around")).toBeInTheDocument();
  });

  it("whispers even though the drawer focuses its input when it opens", () => {
    setSanity(20);
    renderDrawer();

    advancePastOpeningFocus();
    advance(INTRUSIVE_INTERVAL_MS);

    expect(screen.getByPlaceholderText("don't turn around")).toBeInTheDocument();
  });

  it("removes the phrase as soon as the player types", () => {
    setSanity(20);
    renderDrawer();
    advancePastOpeningFocus();
    advance(INTRUSIVE_INTERVAL_MS);

    fireEvent.change(screen.getByPlaceholderText("don't turn around"), {
      target: { value: "I look up" },
    });

    expect(screen.queryByPlaceholderText("don't turn around")).toBeNull();
  });

  it("keeps the standard placeholder at healthy sanity", () => {
    setSanity(90);
    renderDrawer();

    advancePastOpeningFocus();
    advance(INTRUSIVE_INTERVAL_MS * 2);

    expect(screen.getByPlaceholderText(/Action/i).className).not.toContain(
      "placeholder:font-eerie",
    );
  });
});
