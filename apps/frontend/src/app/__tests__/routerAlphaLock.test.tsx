import { render, waitFor } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ALPHA_CONFIG } from "@/test/alphaFixtures";
import { createQueryWrapper } from "@/test/queryWrapper";
import { router } from "../router";

vi.mock("@/shared/lib/firebase", () => ({
  auth: { currentUser: null, signOut: vi.fn() },
  googleProvider: {},
}));

const LOCKED_PATHS = [
  "/studio",
  "/studio/stats",
  "/studio/abc/stats",
  "/studio/new",
  "/studio/abc/edit",
  "/spectate/abc",
  "/join",
];

describe("router in alpha mode", () => {
  it.each(LOCKED_PATHS)("sends %s to Discover", async (path) => {
    const memoryRouter = createMemoryRouter(router.routes, {
      initialEntries: [path],
    });
    const Wrapper = createQueryWrapper(ALPHA_CONFIG);

    render(
      <Wrapper>
        <RouterProvider router={memoryRouter} />
      </Wrapper>,
    );

    await waitFor(() =>
      expect(memoryRouter.state.location.pathname).toBe("/discover"),
    );
  });
});
