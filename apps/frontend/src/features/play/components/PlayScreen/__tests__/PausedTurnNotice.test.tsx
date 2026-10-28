import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { usePlayStore } from "../../../stores/play.store";
import { PausedTurnNotice } from "../EBook/PausedTurnNotice";

const NOTICE_TEXT = "The night desk is closed. Try again later.";

describe("PausedTurnNotice", () => {
  const retryLastTurn = vi.fn();

  beforeEach(() => {
    retryLastTurn.mockReset();
    usePlayStore.setState({
      is_turn_paused: false,
      last_client_action_id: null,
      retryLastTurn,
    });
  });

  it("renders nothing while turns are open", () => {
    render(<PausedTurnNotice />);

    expect(screen.queryByText(NOTICE_TEXT)).not.toBeInTheDocument();
  });

  it("explains the pause inline and offers to try again", async () => {
    usePlayStore.setState({
      is_turn_paused: true,
      last_client_action_id: "action-1",
    });

    render(<PausedTurnNotice />);
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(screen.getByText(NOTICE_TEXT)).toBeInTheDocument();
    expect(retryLastTurn).toHaveBeenCalledTimes(1);
  });

  it("has nothing to retry when no action was submitted", () => {
    usePlayStore.setState({ is_turn_paused: true });

    render(<PausedTurnNotice />);

    expect(screen.getByText(NOTICE_TEXT)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Try again" }),
    ).not.toBeInTheDocument();
  });
});
