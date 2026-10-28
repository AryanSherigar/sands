import { render, screen, fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { StrategyTurnReportLauncher } from "../StrategyTurnReportLauncher";
import { useStrategyPlayStore } from "../../../../stores/strategyPlay.store";

describe("StrategyTurnReportLauncher", () => {
  beforeEach(() => {
    useStrategyPlayStore.getState().reset();
  });

  it("renders Turn report label with shortcut badge [R] and document icon", () => {
    render(<StrategyTurnReportLauncher itemCount={5} />);
    expect(screen.getByText("Turn report")).toBeInTheDocument();
    expect(screen.getByText("[R]")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /turn report/i })).toBeInTheDocument();
  });

  it("shows badge with item count and 'new' when hasUnreadTurnReport is true", () => {
    useStrategyPlayStore.setState({ hasUnreadTurnReport: true });
    render(<StrategyTurnReportLauncher itemCount={12} />);
    expect(screen.getByText("12 new")).toBeInTheDocument();
  });

  it("does not show unread badge when hasUnreadTurnReport is false", () => {
    useStrategyPlayStore.setState({ hasUnreadTurnReport: false });
    render(<StrategyTurnReportLauncher itemCount={12} />);
    expect(screen.queryByText("12 new")).not.toBeInTheDocument();
  });

  it("applies pulse glow styling when unread", () => {
    useStrategyPlayStore.setState({ hasUnreadTurnReport: true });
    render(<StrategyTurnReportLauncher itemCount={12} />);
    const button = screen.getByRole("button", { name: /turn report/i });
    expect(button.className).toContain("animate-pulse");
  });

  it("clicking the launcher toggles the Turn Report in strategyPlay.store", () => {
    render(<StrategyTurnReportLauncher itemCount={3} />);
    const btn = screen.getByRole("button", { name: /turn report/i });
    expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(false);

    fireEvent.click(btn);
    expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(true);

    fireEvent.click(btn);
    expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(false);
  });

  it("pressing KeyR on the window toggles the Turn Report", () => {
    render(<StrategyTurnReportLauncher itemCount={3} />);
    expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(false);

    fireEvent.keyDown(window, { key: "r", code: "KeyR" });
    expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(true);

    fireEvent.keyDown(window, { key: "r", code: "KeyR" });
    expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(false);
  });

  it("does not toggle Turn Report when KeyR is pressed inside an input", () => {
    render(
      <div>
        <input data-testid="test-input" />
        <StrategyTurnReportLauncher itemCount={3} />
      </div>,
    );
    const input = screen.getByTestId("test-input");
    fireEvent.keyDown(input, { key: "r", code: "KeyR" });
    expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(false);
  });
});
