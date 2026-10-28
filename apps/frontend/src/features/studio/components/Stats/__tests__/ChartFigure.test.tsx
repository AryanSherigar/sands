import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ChartFigure } from "../ChartFigure";

describe("ChartFigure", () => {
  it("shows a summary and swaps the chart for a table", async () => {
    render(
      <ChartFigure
        title="Plays over time"
        summary="12 plays in the last 30 days."
        table={{ columns: ["Day", "Plays"], rows: [["Sep 21", "12"]] }}
      >
        <svg role="img" aria-label="plays chart" />
      </ChartFigure>,
    );

    expect(screen.getByText("12 plays in the last 30 days.")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "plays chart" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Show as table" }));

    expect(screen.queryByRole("img", { name: "plays chart" })).not.toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Sep 21" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Show as chart" })).toBeInTheDocument();
  });
});
