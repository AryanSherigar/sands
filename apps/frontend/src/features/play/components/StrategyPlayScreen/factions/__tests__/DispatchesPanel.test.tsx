import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DispatchesPanel } from "../DispatchesPanel";
import type { StrategyDispatchView } from "../../../../types/simulation.types";

const start = vi.fn();
const refetch = vi.fn();
let dispatches: {
  isLoading: boolean;
  isError: boolean;
  data: StrategyDispatchView[];
  refetch: typeof refetch;
};
let stream: {
  streaming: { rumorId: string; narration: string } | null;
  degradedRumorIds: string[];
  start: typeof start;
};

vi.mock("../../../../hooks/useStrategyDispatches", () => ({
  useStrategyDispatches: () => dispatches,
}));
vi.mock("../../../../hooks/useStrategyDispatchStream", () => ({
  useStrategyDispatchStream: () => stream,
}));

const pending = (overrides: Partial<StrategyDispatchView> = {}): StrategyDispatchView => ({
  rumor_id: "rumor_1",
  turn: 3,
  agent: { name: "Aldous", traits: ["honest", "pious"] },
  about_faction_id: "house_dunwick",
  topic: "will",
  status: "pending",
  narration: null,
  fallback_line_key: "will.high",
  error_code: null,
  ...overrides,
});

describe("DispatchesPanel", () => {
  beforeEach(() => {
    start.mockReset();
    refetch.mockReset();
    dispatches = { isLoading: false, isError: false, data: [], refetch };
    stream = { streaming: null, degradedRumorIds: [], start };
  });

  it("shows an empty state", () => {
    render(<DispatchesPanel playthroughId="pt-1" />);
    expect(screen.getByText("No dispatches yet")).toBeInTheDocument();
  });

  it("shows the agent, visible traits, rival and turn", () => {
    dispatches.data = [pending()];
    render(<DispatchesPanel playthroughId="pt-1" />);
    expect(screen.getByText("House Dunwick")).toBeInTheDocument();
    expect(screen.getByText(/Aldous/)).toBeInTheDocument();
    expect(screen.getByText(/honest, pious/)).toBeInTheDocument();
    expect(screen.getByText("Turn 4")).toBeInTheDocument();
  });

  it("groups dispatches about the same rival under one heading", () => {
    dispatches.data = [pending(), pending({ rumor_id: "rumor_2", agent: { name: "Maren", traits: ["deceitful"] } })];
    render(<DispatchesPanel playthroughId="pt-1" />);
    expect(screen.getAllByText("House Dunwick")).toHaveLength(1);
    expect(screen.getByText(/Maren/)).toBeInTheDocument();
  });

  it("starts reading a pending dispatch", () => {
    dispatches.data = [pending()];
    render(<DispatchesPanel playthroughId="pt-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Read dispatch" }));
    expect(start).toHaveBeenCalledWith(dispatches.data[0]);
  });

  it("shows streamed text while a dispatch is being written", () => {
    dispatches.data = [pending()];
    stream.streaming = { rumorId: "rumor_1", narration: "My lord, the border" };
    render(<DispatchesPanel playthroughId="pt-1" />);
    expect(screen.getByText("My lord, the border")).toBeInTheDocument();
  });

  it("shows saved text for a completed dispatch with no read button", () => {
    dispatches.data = [pending({ status: "completed", narration: "All is calm." })];
    render(<DispatchesPanel playthroughId="pt-1" />);
    expect(screen.getByText("All is calm.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Read dispatch" })).toBeNull();
  });

  it("falls back to a short note when writing failed", () => {
    dispatches.data = [pending({ status: "failed" })];
    stream.degradedRumorIds = ["rumor_1"];
    render(<DispatchesPanel playthroughId="pt-1" />);
    expect(screen.getByText(/short note/i)).toBeInTheDocument();
    expect(screen.getByText(/resolve/i)).toBeInTheDocument();
  });

  it("never renders hidden state even if the payload carried it", () => {
    const leaky = { ...pending(), bribed_by: "house_carrow", loyalty: 99 } as StrategyDispatchView;
    dispatches.data = [leaky];
    const { container } = render(<DispatchesPanel playthroughId="pt-1" />);
    expect(container.textContent).not.toMatch(/bribe|loyalty|99|house_carrow/i);
  });

  it("offers a retry when the list cannot load", () => {
    dispatches.isError = true;
    render(<DispatchesPanel playthroughId="pt-1" />);
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(refetch).toHaveBeenCalled();
  });
});
