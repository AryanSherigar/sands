import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createQueryWrapper } from "@/test/queryWrapper";
import { ALPHA_CONFIG, NON_ALPHA_CONFIG } from "@/test/alphaFixtures";
import type { AlphaConfig } from "@/shared/types/alpha.types";
import { PlaythroughEndedBanner } from "../PlaythroughEndedBanner";

const renderBanner = (config: AlphaConfig): void => {
  render(
    <PlaythroughEndedBanner
      outcomeTag="win"
      outcomeTitle="Uncounted"
      outcomeText="Dawn."
      playthroughId="pt-1"
      onBackToLibrary={vi.fn()}
    />,
    { wrapper: createQueryWrapper(config) },
  );
};

describe("PlaythroughEndedBanner", () => {
  it("offers the post-run survey in alpha mode", async () => {
    const user = userEvent.setup();
    renderBanner(ALPHA_CONFIG);

    await user.click(screen.getByRole("button", { name: "Rate this run" }));

    expect(screen.getByRole("dialog", { name: "How was this run?" })).toBeInTheDocument();
  });

  it("has no survey button outside alpha mode", () => {
    renderBanner(NON_ALPHA_CONFIG);

    expect(screen.queryByRole("button", { name: "Rate this run" })).toBeNull();
  });
});
