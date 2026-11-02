import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ReservesDeck } from "../ReservesDeck";

describe("ReservesDeck", () => {
  it("changes the reserve policy and commits reserves", () => {
    const handlePolicy = vi.fn();
    const handleCommit = vi.fn();
    render(
      <ReservesDeck
        reservePolicy="conserve"
        onChangePolicy={handlePolicy}
        canCommitReserves
        onCommitReserves={handleCommit}
      />,
    );

    fireEvent.click(screen.getByRole("radio", { name: "Reinforce under pressure" }));
    fireEvent.click(screen.getByRole("button", { name: "Commit reserves now" }));

    expect(handlePolicy).toHaveBeenCalledWith("reinforce_on_pressure");
    expect(handleCommit).toHaveBeenCalledTimes(1);
  });

  it("disables the commit button when the command is not legal", () => {
    render(
      <ReservesDeck
        reservePolicy="conserve"
        onChangePolicy={vi.fn()}
        canCommitReserves={false}
        onCommitReserves={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Commit reserves now" })).toBeDisabled();
  });
});
