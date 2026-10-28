import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { StrategyCampaignLoader } from "../StrategyCampaignLoader";
import { STRATEGY_TIPS, STRATEGY_LOADER_STAGES } from "../strategyTips.constants";

describe("StrategyCampaignLoader", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders atmospheric transition overlay with status and strategy tips", () => {
    render(<StrategyCampaignLoader status="Inscribing the Royal Covenant..." />);
    expect(screen.getByText("Inscribing the Royal Covenant...")).toBeDefined();
    expect(screen.getByTestId("strategy-tip-card")).toBeDefined();
    expect(screen.getByTestId("golden-wax-seal")).toBeDefined();
  });

  it("cycles progressive status stages when no status prop is provided", () => {
    render(<StrategyCampaignLoader />);
    expect(screen.getByText(STRATEGY_LOADER_STAGES[0])).toBeDefined();

    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(screen.getByText(STRATEGY_LOADER_STAGES[1])).toBeDefined();

    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(screen.getByText(STRATEGY_LOADER_STAGES[2])).toBeDefined();
  });

  it("rotates strategy tips every 4 seconds", () => {
    render(<StrategyCampaignLoader status="Inscribing the Royal Covenant..." />);

    // Initial tip displayed
    expect(screen.getByText(STRATEGY_TIPS[0].text)).toBeDefined();

    // Advance 4 seconds
    act(() => {
      vi.advanceTimersByTime(4000);
    });
    expect(screen.getByText(STRATEGY_TIPS[1].text)).toBeDefined();

    // Advance another 4 seconds
    act(() => {
      vi.advanceTimersByTime(4000);
    });
    expect(screen.getByText(STRATEGY_TIPS[2].text)).toBeDefined();
  });

  it("renders wax seal emblem and mist atmospheric background elements", () => {
    const { container } = render(<StrategyCampaignLoader status="Unfurling the Frontier Wilds..." />);
    const seal = screen.getByTestId("golden-wax-seal");
    expect(seal).toBeDefined();

    // Verify presence of mist/atmospheric blur containers
    const mistOverlays = container.querySelectorAll(".blur-3xl");
    expect(mistOverlays.length).toBeGreaterThanOrEqual(2);
  });
});
