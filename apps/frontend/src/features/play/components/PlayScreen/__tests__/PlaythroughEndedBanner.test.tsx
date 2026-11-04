import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PlaythroughEndedBanner } from "../PlaythroughEndedBanner";

describe("PlaythroughEndedBanner", () => {
  it("shows the outcome and returns to the library", async () => {
    const user = userEvent.setup();
    const onBackToLibrary = vi.fn();
    render(
      <PlaythroughEndedBanner
        outcomeTag="win"
        outcomeTitle="Uncounted"
        outcomeText="Dawn."
        onBackToLibrary={onBackToLibrary}
      />,
    );

    expect(screen.getByText("Uncounted")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Return to Library" }));

    expect(onBackToLibrary).toHaveBeenCalledOnce();
  });
});
