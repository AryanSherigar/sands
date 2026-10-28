import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TierPips } from "./TierPips";

const options = ["uneasy", "tense", "dread", "breaking"];

describe("TierPips", () => {
  it("names the current tier as text, not colour only", () => {
    render(<TierPips label="Tension" options={options} value="dread" />);

    expect(screen.getByRole("group", { name: "Tension dread" })).toBeInTheDocument();
    expect(screen.getAllByText("dread").length).toBeGreaterThan(0);
  });

  it("renders one pip per option and marks only the current one", () => {
    const { container } = render(
      <TierPips label="Tension" options={options} value="tense" />,
    );

    expect(container.querySelectorAll("li")).toHaveLength(4);
    const active = container.querySelectorAll('li[data-active="true"]');
    expect(active).toHaveLength(1);
    expect(active[0]).toHaveTextContent("tense");
  });
});
