import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ALPHA_CONFIG, NON_ALPHA_CONFIG } from "@/test/alphaFixtures";
import { createQueryWrapper } from "@/test/queryWrapper";
import type { AlphaConfig } from "@/shared/types/alpha.types";
import type { DiscoverFilters } from "../../../types/discover.types";
import { DiscoverEmptyState } from "../DiscoverEmptyState";

const CREATED_FILTERS: DiscoverFilters = {
  query: "",
  genres: [],
  type: null,
  library: "created",
  sort: "new",
  isMatureIncluded: false,
};

const renderEmpty = (config: AlphaConfig): void => {
  const Wrapper = createQueryWrapper(config);
  render(
    <Wrapper>
      <MemoryRouter>
        <DiscoverEmptyState
          filters={CREATED_FILTERS}
          hasActiveFilters={false}
          onClearFilters={vi.fn()}
          onExploreTopRated={vi.fn()}
        />
      </MemoryRouter>
    </Wrapper>,
  );
};

describe("DiscoverEmptyState created library", () => {
  it("links to Studio when alpha mode is off", () => {
    renderEmpty(NON_ALPHA_CONFIG);
    expect(screen.getByRole("link", { name: "New Story" })).toBeInTheDocument();
  });

  it("offers no Studio link in alpha mode", () => {
    renderEmpty(ALPHA_CONFIG);
    expect(screen.queryByRole("link", { name: "New Story" })).toBeNull();
  });
});
