import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ALPHA_CONFIG, NON_ALPHA_CONFIG } from "@/test/alphaFixtures";
import { createQueryWrapper } from "@/test/queryWrapper";
import type { AlphaConfig } from "@/shared/types/alpha.types";
import { LandingEmptyState } from "../LandingEmptyState";
import { StudioShowcaseBand } from "../StudioShowcaseBand";

vi.mock("../StudioWorkbenchPreview", () => ({
  StudioWorkbenchPreview: () => <div>workbench preview</div>,
}));

const renderWith = (config: AlphaConfig, ui: React.ReactElement): void => {
  const Wrapper = createQueryWrapper(config);
  render(
    <Wrapper>
      <MemoryRouter>{ui}</MemoryRouter>
    </Wrapper>,
  );
};

describe("StudioShowcaseBand", () => {
  it("is shown when alpha mode is off", () => {
    renderWith(NON_ALPHA_CONFIG, <StudioShowcaseBand />);
    expect(screen.getByRole("link", { name: /open studio/i })).toBeInTheDocument();
  });

  it("is hidden in alpha mode", () => {
    renderWith(ALPHA_CONFIG, <StudioShowcaseBand />);
    expect(screen.queryByRole("link", { name: /open studio/i })).toBeNull();
    expect(screen.queryByText("workbench preview")).toBeNull();
  });
});

describe("LandingEmptyState", () => {
  it("invites the visitor to create a story when alpha mode is off", () => {
    renderWith(NON_ALPHA_CONFIG, <LandingEmptyState />);
    expect(screen.getByRole("button", { name: "New Story" })).toBeInTheDocument();
  });

  it("offers no creation entry point in alpha mode", () => {
    renderWith(ALPHA_CONFIG, <LandingEmptyState />);
    expect(screen.queryByRole("button", { name: "New Story" })).toBeNull();
    expect(screen.queryByText("Be the first to create one.")).toBeNull();
  });
});
