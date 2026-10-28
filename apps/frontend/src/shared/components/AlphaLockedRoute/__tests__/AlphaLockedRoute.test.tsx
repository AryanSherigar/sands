import { render, screen } from "@testing-library/react";
import { delay, http } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { ALPHA_CONFIG, NON_ALPHA_CONFIG } from "@/test/alphaFixtures";
import { createQueryWrapper } from "@/test/queryWrapper";
import type { AlphaConfig } from "@/shared/types/alpha.types";
import { AlphaLockedRoute } from "../AlphaLockedRoute";

const renderRoute = (config?: AlphaConfig): void => {
  const Wrapper = createQueryWrapper(config);
  render(
    <Wrapper>
      <MemoryRouter initialEntries={["/studio"]}>
        <Routes>
          <Route
            path="/studio"
            element={
              <AlphaLockedRoute>
                <p>studio content</p>
              </AlphaLockedRoute>
            }
          />
          <Route path="/discover" element={<p>discover page</p>} />
        </Routes>
      </MemoryRouter>
    </Wrapper>,
  );
};

describe("AlphaLockedRoute", () => {
  it("renders the page when alpha mode is off", () => {
    renderRoute(NON_ALPHA_CONFIG);
    expect(screen.getByText("studio content")).toBeInTheDocument();
  });

  it("redirects to Discover in alpha mode", () => {
    renderRoute(ALPHA_CONFIG);
    expect(screen.getByText("discover page")).toBeInTheDocument();
    expect(screen.queryByText("studio content")).toBeNull();
  });

  it("shows nothing while the config is still loading", () => {
    server.use(
      http.get("*/v1/alpha/config", async () => {
        await delay("infinite");
      }),
    );
    renderRoute();
    expect(screen.queryByText("studio content")).toBeNull();
    expect(screen.queryByText("discover page")).toBeNull();
  });

  it("renders the page when the config cannot be loaded", async () => {
    server.use(
      http.get(
        "*/v1/alpha/config",
        () => new Response(null, { status: 500 }),
      ),
    );
    renderRoute();
    expect(
      await screen.findByText("studio content", {}, { timeout: 4000 }),
    ).toBeInTheDocument();
  });
});
