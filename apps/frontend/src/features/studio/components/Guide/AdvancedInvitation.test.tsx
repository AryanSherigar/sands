import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AdvancedInvitation } from "./AdvancedInvitation";

const renderInvitation = (isPublishing: boolean) => {
  const onAccept = vi.fn();
  render(
    <AdvancedInvitation
      canUseAdvanced
      isPublishing={isPublishing}
      isBusy={false}
      onAccept={onAccept}
      onDecline={vi.fn()}
    />,
  );
  return onAccept;
};

describe("AdvancedInvitation", () => {
  it("turns Advanced mode on when the story is not publishing", async () => {
    const onAccept = renderInvitation(false);
    await userEvent.setup().click(screen.getByRole("button", { name: "Turn on Advanced mode" }));
    expect(onAccept).toHaveBeenCalledTimes(1);
  });

  it("disables the button and says why while the story is publishing", async () => {
    const onAccept = renderInvitation(true);
    const button = screen.getByRole("button", { name: "Turn on Advanced mode" });

    expect(button).toBeDisabled();
    expect(screen.getByText("Publishing… editing unlocks when it's done.")).toBeInTheDocument();
    await userEvent.setup().click(button);
    expect(onAccept).not.toHaveBeenCalled();
  });
});
