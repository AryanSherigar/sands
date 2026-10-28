import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EBookBottomBar } from "../EBook/EBookBottomBar";

describe("EBookBottomBar", () => {
  it("renders spectator message when isSpectator is true", () => {
    render(<EBookBottomBar isSpectator={true} />);

    expect(
      screen.getByText(/You are currently spectating this chronicle/i),
    ).toBeInTheDocument();
  });

  it("renders a waiting message when canAct is false", () => {
    render(
      <EBookBottomBar
        isSpectator={false}
        canAct={false}
        waitingOnLabel="Player 2"
      />,
    );

    expect(screen.getByText(/Waiting for Player 2/i)).toBeInTheDocument();
  });

  it("renders the ended message once the chronicle has ended", () => {
    render(<EBookBottomBar isSpectator={false} isEnded={true} />);

    expect(screen.getByText(/This chronicle has ended/i)).toBeInTheDocument();
  });
});
