import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { NegotiationHeader } from "../NegotiationHeader";

describe("NegotiationHeader", () => {
  it("renders title, exit button, and exchange counter", () => {
    const handleExit = vi.fn();
    render(
      <NegotiationHeader
        title="Peace Talks with Queen Mira"
        exchangesRemaining={3}
        totalExchanges={6}
        isFinished
        onExit={handleExit}
      />
    );

    expect(screen.getByText("Peace Talks with Queen Mira")).toBeInTheDocument();
    expect(screen.getByText("Exit to Encampment")).toBeInTheDocument();
    expect(screen.getByText("3 of 6")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Exit to Encampment"));
    expect(handleExit).toHaveBeenCalledTimes(1);
  });

  it("disables exit button until the scene is finished", () => {
    render(
      <NegotiationHeader
        title="Forced Audience"
        exchangesRemaining={4}
        isFinished={false}
        onExit={vi.fn()}
      />
    );

    const exitBtn = screen.getByRole("button", { name: /exit to encampment/i });
    expect(exitBtn).toBeDisabled();
  });
});
