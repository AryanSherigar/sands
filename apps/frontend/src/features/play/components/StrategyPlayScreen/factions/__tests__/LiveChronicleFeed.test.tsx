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
    refetch.mockReset();
    summaries = { isLoading: false, isError: false, data: { items: [] }, refetch };
    stream = { streaming: null, error: null, start };
  });

  it("shows an intentional empty state", () => {
    render(<LiveChronicleFeed playthroughId="playthrough-1" onJumpToRegion={vi.fn()} />);
    expect(screen.getByText("No chronicle entries yet")).toBeInTheDocument();
  });

  it("starts a pending entry and permits only its safe map region", () => {
    summaries = { ...summaries, data: { items: [pendingSummary] } };
    const onJumpToRegion = vi.fn();
    render(<LiveChronicleFeed playthroughId="playthrough-1" onJumpToRegion={onJumpToRegion} />);

    fireEvent.click(screen.getByRole("button", { name: "Write entry" }));
    fireEvent.click(screen.getByRole("button", { name: "Map" }));

    expect(start).toHaveBeenCalledWith(pendingSummary);
    expect(onJumpToRegion).toHaveBeenCalledWith("reg-dunmere");
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
});
