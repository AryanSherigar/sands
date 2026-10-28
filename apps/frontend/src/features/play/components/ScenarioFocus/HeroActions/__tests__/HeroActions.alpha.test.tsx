import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ALPHA_CONFIG, NON_ALPHA_CONFIG } from "@/test/alphaFixtures";
import { createQueryWrapper } from "@/test/queryWrapper";
import type { AlphaConfig } from "@/shared/types/alpha.types";
import { HeroActions } from "../HeroActions";

const renderActions = (config: AlphaConfig): void => {
  const Wrapper = createQueryWrapper(config);
  render(
    <Wrapper>
      <MemoryRouter>
        <HeroActions
          scenarioId="s1"
          isOwner
          isDraft={false}
          isBookmarked={false}
          isTogglingBookmark={false}
          isStartingPlaytest={false}
          onToggleBookmark={vi.fn()}
          onShare={vi.fn()}
          onPlaytest={vi.fn()}
        />
      </MemoryRouter>
    </Wrapper>,
  );
};

describe("HeroActions in alpha mode", () => {
  it("offers Share and Edit in Studio when alpha mode is off", () => {
    renderActions(NON_ALPHA_CONFIG);
    expect(screen.getByRole("button", { name: /share/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /edit in studio/i })).toBeInTheDocument();
  });

  it("hides Share and Edit in Studio but keeps Save and Play", () => {
    renderActions(ALPHA_CONFIG);
    expect(screen.queryByRole("button", { name: /share/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /edit in studio/i })).toBeNull();
    expect(screen.getByRole("button", { name: /save/i })).toBeInTheDocument();
  });
});
