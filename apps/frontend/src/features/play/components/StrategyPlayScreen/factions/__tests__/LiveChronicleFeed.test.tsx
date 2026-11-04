import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LiveChronicleFeed } from "../LiveChronicleFeed";
import type { StrategySummaryPage, StrategySummaryView } from "../../../../types/simulation.types";

const start = vi.fn();
const refetch = vi.fn();
let summaries: {
  isLoading: boolean;
  isError: boolean;
  data: StrategySummaryPage;
  refetch: typeof refetch;
} = {
  isLoading: false,
  isError: false,
  data: { items: [] },
  refetch,
};
let stream: {
  streaming: { summaryId: string; narration: string } | null;
  error: { code: string; message: string; is_retryable: boolean } | null;
  start: typeof start;
} = { streaming: null, error: null, start };

const useStrategyArt = vi.fn();
vi.mock("../../../../hooks/useStrategyArt", () => ({
  useStrategyArt: (...args: unknown[]) => useStrategyArt(...args),
}));
vi.mock("../../../../hooks/useStrategySummaries", () => ({
  useStrategySummaries: () => summaries,
  useStrategySummaryStream: () => stream,
}));

const pendingSummary: StrategySummaryView = {
  summary_id: "summary-1",
  requested_turn: 3,
  trigger: "major_event" as const,
  status: "pending" as const,
  narration: null,
  error_code: null,
  is_retryable: true,
  region_ids: ["reg-dunmere"],
};

describe("LiveChronicleFeed", () => {
  beforeEach(() => {
    start.mockReset();
    useStrategyArt.mockReset();
    useStrategyArt.mockReturnValue({ artUrl: null, isLoading: false });
    refetch.mockReset();
    summaries = { isLoading: false, isError: false, data: { items: [] }, refetch };
    stream = { streaming: null, error: null, start };
  });

  it("shows an intentional empty state", () => {
    render(<LiveChronicleFeed playthroughId="playthrough-1" onJumpToRegion={vi.fn()} />);
    expect(screen.getByText("No chronicle entries yet")).toBeInTheDocument();
  });

  it("starts a pending entry with no chronicler choice and offers no selector", () => {
    summaries = { ...summaries, data: { items: [pendingSummary] } };
    const onJumpToRegion = vi.fn();
    render(
      <LiveChronicleFeed
        playthroughId="playthrough-1"
        chroniclerId="vaelen"
        onJumpToRegion={onJumpToRegion}
      />,
    );

    expect(screen.queryByLabelText("Select Chronicler")).toBeNull();
    expect(screen.getByText(/Ready to be recorded by Vaelen the Scorned/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Write entry" }));
    expect(start).toHaveBeenCalledWith(pendingSummary);

    fireEvent.click(screen.getByRole("button", { name: "Map" }));
    expect(onJumpToRegion).toHaveBeenCalledWith("reg-dunmere");
  });

  it("names Brother Lucan when the world carries no chronicler", () => {
    summaries = { ...summaries, data: { items: [pendingSummary] } };
    render(<LiveChronicleFeed playthroughId="playthrough-1" onJumpToRegion={vi.fn()} />);
    expect(screen.getByText(/Ready to be recorded by Brother Lucan/)).toBeInTheDocument();
  });

  it("keeps provisional streamed prose visible and reports recoverable errors", () => {
    summaries = { ...summaries, data: { items: [pendingSummary] } };
    stream = {
      streaming: { summaryId: "summary-1", narration: "A storm gathers." },
      error: { code: "provider_timeout", message: "Chronicle could not be saved. Try again.", is_retryable: true },
      start,
    };
    render(<LiveChronicleFeed playthroughId="playthrough-1" onJumpToRegion={vi.fn()} />);

    expect(screen.getByText("A storm gathers.")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Chronicle could not be saved");
  });

  it("requests art only for the entry the player chooses to illustrate", () => {
    const completed = (id: string): StrategySummaryView => ({
      ...pendingSummary,
      summary_id: id,
      status: "completed",
      narration: "The realm stirs.",
    });
    summaries = { ...summaries, data: { items: [completed("summary-1"), completed("summary-2")] } };
    render(<LiveChronicleFeed playthroughId="playthrough-1" onJumpToRegion={vi.fn()} />);

    expect(useStrategyArt).not.toHaveBeenCalled();
    fireEvent.click(screen.getAllByRole("button", { name: "Illustrate" })[0]);

    expect(useStrategyArt).toHaveBeenCalledWith("playthrough-1", "chronicle", "summary-1");
    expect(useStrategyArt).not.toHaveBeenCalledWith("playthrough-1", "chronicle", "summary-2");
  });
});
