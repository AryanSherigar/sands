import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { ALPHA_CONFIG, NON_ALPHA_CONFIG } from "@/test/alphaFixtures";
import { createQueryWrapper } from "@/test/queryWrapper";
import type { AlphaConfig } from "@/shared/types/alpha.types";
import { CreationsTab } from "../CreationsTab";

const renderTab = (config: AlphaConfig): void => {
  server.use(
    http.get("*/v1/scenarios", () =>
      HttpResponse.json({ items: [], next_cursor: null, total_count: 0 }),
    ),
  );
  const Wrapper = createQueryWrapper(config);
  render(
    <Wrapper>
      <MemoryRouter>
        <CreationsTab userId="u1" isOwner />
      </MemoryRouter>
    </Wrapper>,
  );
};

describe("CreationsTab owner actions", () => {
  it("links to Studio when alpha mode is off", async () => {
    renderTab(NON_ALPHA_CONFIG);
    expect(await screen.findByRole("link", { name: "Manage in Studio" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "New Story" })).toBeInTheDocument();
  });

  it("offers no Studio or create links in alpha mode", async () => {
    renderTab(ALPHA_CONFIG);
    expect(await screen.findByText("No stories yet")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Manage in Studio" })).toBeNull();
    expect(screen.queryByRole("link", { name: "New Story" })).toBeNull();
  });
});
