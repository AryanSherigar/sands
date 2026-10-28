import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { IconCoin, IconShield } from "@tabler/icons-react";
import { StatChip } from "../StatChip";

describe("StatChip", () => {
  it("renders icon, value, and trend", () => {
    render(
      <StatChip
        icon={<IconCoin data-testid="coin-icon" size={14} />}
        value="500"
        trend="+25/mo"
        tooltipTitle="Gold Reserves"
        tooltipDesc="Current treasury balance."
      />,
    );
    expect(screen.getByTestId("coin-icon")).toBeInTheDocument();
    expect(screen.getByText("500")).toBeInTheDocument();
    expect(screen.getByText("+25/mo")).toBeInTheDocument();
    expect(screen.getByText("Gold Reserves")).toBeInTheDocument();
    expect(screen.getByText("Current treasury balance.")).toBeInTheDocument();
  });

  it("renders without trend when not provided", () => {
    render(
      <StatChip
        icon={<IconShield data-testid="shield-icon" size={14} />}
        value="10,000"
        tooltipTitle="Manpower"
        tooltipDesc="Total levies."
      />,
    );
    expect(screen.getByTestId("shield-icon")).toBeInTheDocument();
    expect(screen.getByText("10,000")).toBeInTheDocument();
  });
});
