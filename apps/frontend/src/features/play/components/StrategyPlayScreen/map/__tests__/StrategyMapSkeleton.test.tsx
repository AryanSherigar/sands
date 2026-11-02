import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StrategyMapSkeleton } from "../StrategyMapSkeleton";

describe("StrategyMapSkeleton", () => {
  it("renders default cartography loading message", () => {
    render(<StrategyMapSkeleton />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByText("Unfurling realm cartography...")).toBeInTheDocument();
  });

  it("renders custom loading message when provided", () => {
    render(<StrategyMapSkeleton message="Tracing mountain passes..." />);
    expect(screen.getByText("Tracing mountain passes...")).toBeInTheDocument();
  });

  it("applies parchment background and custom classes", () => {
    render(<StrategyMapSkeleton className="custom-map-loader" />);
    const root = screen.getByTestId("strategy-map-skeleton");
    expect(root).toHaveClass("bg-[#ECE4D0]");
    expect(root).toHaveClass("custom-map-loader");
  });
});
