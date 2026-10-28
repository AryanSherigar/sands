import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ShareStoryButton } from "../ShareStoryButton";

describe("ShareStoryButton", () => {
  it("copies the public scenario link", async () => {
    const user = userEvent.setup();
    render(<ShareStoryButton scenarioId="scn-1" />);

    await user.click(screen.getByRole("button", { name: "Share your story" }));

    expect(await screen.findByText("Link copied")).toBeInTheDocument();
    expect(await navigator.clipboard.readText()).toBe(
      `${window.location.origin}/scenario/scn-1`,
    );
  });
});
