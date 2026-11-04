import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DeploymentSummary } from "../DeploymentSummary";

describe("DeploymentSummary", () => {
  it("lists what is in the line and what is held back, by troop type", () => {
    render(
      <DeploymentSummary
        active={{ infantry: 1200, cavalry: 150 }}
        reserve={{ archers_siege: 300 }}
      />,
    );

    expect(screen.getByText("In the line")).toBeInTheDocument();
    expect(screen.getByText("1,200")).toBeInTheDocument();
    expect(screen.getByText("Held in reserve")).toBeInTheDocument();
    expect(screen.getByText("Archers & siege")).toBeInTheDocument();
  });

  it("says none when nothing is held in reserve, and renders nothing without data", () => {
    const { container, rerender } = render(<DeploymentSummary active={{ infantry: 10 }} reserve={{}} />);
    expect(screen.getByText("None")).toBeInTheDocument();

    rerender(<DeploymentSummary />);
    expect(container).toBeEmptyDOMElement();
  });
});
