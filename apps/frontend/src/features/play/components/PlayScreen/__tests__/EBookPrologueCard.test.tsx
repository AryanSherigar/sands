import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EBookPrologueCard } from "../EBook/EBookPrologueCard";

describe("EBookPrologueCard", () => {
  it("renders scenario premise", () => {
    const handleStartAction = vi.fn();

    render(
      <EBookPrologueCard
        premise="The shadowed towers of Ravenloft loom amidst the weeping fog."
        onStartAction={handleStartAction}
      />,
    );

    expect(screen.getByText(/Prologue/i)).toBeInTheDocument();
    expect(
      screen.getByText(
        /The shadowed towers of Ravenloft loom amidst the weeping fog/i,
      ),
    ).toBeInTheDocument();

    const startButton = screen.getByRole("button", {
      name: /Begin First Action/i,
    });
    fireEvent.click(startButton);
    expect(handleStartAction).toHaveBeenCalledTimes(1);
  });
});
