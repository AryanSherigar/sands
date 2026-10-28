import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { usePlayStore } from "../../../stores/play.store";
import { MinigameOverlay } from "../MinigameOverlay";

// Mocked here purely so this file's import graph resolves; MinigameOverlay's
// dodge minigame branch is out of scope for this test file.
vi.mock("@/shared/components/minigames/DodgeMinigame/DodgeMinigame", () => ({
  DodgeMinigame: () => <div data-testid="dodge-minigame-stub" />,
}));

const composureProps = vi.hoisted(() => ({
  latest: null as null | { onComplete: (r: unknown) => void; config: unknown },
}));
vi.mock("@/shared/components/minigames/ComposureMinigame/ComposureMinigame", () => ({
  ComposureMinigame: (props: {
    composureConfig: unknown;
    onComplete: (r: unknown) => void;
  }) => {
    composureProps.latest = {
      onComplete: props.onComplete,
      config: props.composureConfig,
    };
    return <div data-testid="composure-minigame-stub" />;
  },
}));

vi.mock("@/shared/hooks/useDefaultMoodTracks", () => ({
  useDefaultMoodTracks: () => ({ data: undefined }),
}));

const mockSubmit = vi.fn();
vi.mock("../../../hooks/useMinigameResult", () => ({
  useMinigameResult: () => ({
    submit: mockSubmit,
    retry: vi.fn(),
    submitTimeoutFallback: vi.fn(),
  }),
}));

function resetStore(): void {
  mockSubmit.mockClear();
  usePlayStore.setState({
    active_minigame: null,
  });
}

describe("MinigameOverlay", () => {
  beforeEach(() => {
    resetStore();
  });

  it("renders nothing when active_minigame is null", () => {
    const { container } = render(<MinigameOverlay />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the dodge branch when active_minigame is a dodge minigame", () => {
    usePlayStore.setState({
      active_minigame: {
        minigame_id: "mg-2",
        minigame_type: "dodge",
        label: "Warden's Onslaught",
        dodge_config: { difficulty: 3 },
        timeout_seconds: 30,
      },
    });

    render(<MinigameOverlay />);
    expect(screen.getByTestId("dodge-minigame-stub")).toBeInTheDocument();
  });

  it("renders the top bar header with label and allows forfeiting as a timeout", () => {
    usePlayStore.setState({
      active_minigame: {
        minigame_id: "mg-1",
        minigame_type: "dodge",
        label: "Rune Strike Challenge",
        dodge_config: { difficulty: 3 },
        timeout_seconds: 20,
        attempt_id: "attempt-123",
      },
    });

    render(<MinigameOverlay />);
    expect(screen.getByText("Rune Strike Challenge")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /forfeit/i })).toBeInTheDocument();

    // Click Forfeit to open confirmation modal
    fireEvent.click(screen.getByRole("button", { name: /forfeit/i }));
    expect(screen.getByText(/Forfeit Challenge\?/i)).toBeInTheDocument();

    // Click "Keep Playing" to dismiss
    fireEvent.click(screen.getByRole("button", { name: /keep playing/i }));
    expect(screen.queryByText(/Forfeit Challenge\?/i)).not.toBeInTheDocument();
    expect(mockSubmit).not.toHaveBeenCalled();

    // Open again and confirm forfeit
    fireEvent.click(screen.getByRole("button", { name: /forfeit/i }));
    fireEvent.click(screen.getByRole("button", { name: /yes, forfeit/i }));

    expect(mockSubmit).toHaveBeenCalledWith({
      minigame_id: "mg-1",
      attempt_id: "attempt-123",
      outcome_tag: "timeout",
    });
  });

  it("renders the composure branch and forwards its result through submit", () => {
    const composureConfig = {
      target_bpm: 50,
      beats_to_win: 4,
      tolerance_ms: 200,
      max_strikes: 2,
      keys: ["W"],
      audio_profile: "chase",
      texts: {
        instructions: "Hum.",
        start_text: "Begin",
        win_text: "Calm.",
        lose_text: "Broken.",
      },
    };
    usePlayStore.setState({
      active_minigame: {
        minigame_id: "mg-hum",
        minigame_type: "rhythm_composure",
        label: "The stairwell hum",
        composure_config: composureConfig,
        timeout_seconds: 20,
        attempt_id: "attempt-9",
      },
    } as never);

    render(<MinigameOverlay />);
    expect(screen.getByTestId("composure-minigame-stub")).toBeInTheDocument();
    expect(composureProps.latest?.config).toEqual(composureConfig);

    composureProps.latest?.onComplete({ outcome_tag: "win", score: 4 });

    expect(mockSubmit).toHaveBeenCalledWith({
      minigame_id: "mg-hum",
      attempt_id: "attempt-9",
      outcome_tag: "win",
      score: 4,
    });
  });

  it("renders no game for a composure minigame that arrived without its config", () => {
    usePlayStore.setState({
      active_minigame: {
        minigame_id: "mg-hum",
        minigame_type: "rhythm_composure",
        label: "The stairwell hum",
        timeout_seconds: 20,
      },
    });

    render(<MinigameOverlay />);

    expect(screen.queryByTestId("composure-minigame-stub")).toBeNull();
  });
});
