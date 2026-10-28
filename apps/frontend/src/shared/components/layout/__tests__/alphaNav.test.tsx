import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ALPHA_CONFIG, NON_ALPHA_CONFIG } from "@/test/alphaFixtures";
import { createQueryWrapper } from "@/test/queryWrapper";
import type { AlphaConfig } from "@/shared/types/alpha.types";
import { AvatarMenu } from "../AvatarMenu";
import { Footer } from "../Footer";
import { MobileTabBar } from "../MobileTabBar";
import { TopBar } from "../TopBar";

vi.mock("@/features/auth/hooks/useAuth", () => ({
  useAuth: () => ({ user: { user_id: "u1", display_name: "Tester" } }),
}));
vi.mock("../AccountSlot", () => ({ AccountSlot: () => null }));
vi.mock("../SearchField", () => ({ SearchField: () => null }));

const renderWith = (config: AlphaConfig, ui: React.ReactElement): void => {
  const Wrapper = createQueryWrapper(config);
  render(
    <Wrapper>
      <MemoryRouter>{ui}</MemoryRouter>
    </Wrapper>,
  );
};

describe.each([
  ["TopBar", <TopBar key="t" isTransparent={false} isCondensed={false} />],
  ["MobileTabBar", <MobileTabBar key="m" />],
  ["Footer", <Footer key="f" />],
])("%s Studio link", (_name, element) => {
  it("is shown when alpha mode is off", () => {
    renderWith(NON_ALPHA_CONFIG, element);
    expect(screen.getByRole("link", { name: "Studio" })).toBeInTheDocument();
  });

  it("is hidden in alpha mode while Discover stays", () => {
    renderWith(ALPHA_CONFIG, element);
    expect(screen.queryByRole("link", { name: "Studio" })).toBeNull();
    expect(screen.getByRole("link", { name: "Discover" })).toBeInTheDocument();
  });
});

describe("AvatarMenu", () => {
  const user = { user_id: "u1", display_name: "Tester", onboarding_completed: true };

  it("lists creator entries when alpha mode is off", async () => {
    renderWith(NON_ALPHA_CONFIG, <AvatarMenu user={user} onSignOut={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Account menu" }));
    expect(screen.getByRole("menuitem", { name: "My scenarios" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Creator stats" })).toBeInTheDocument();
  });

  it("hides creator entries in alpha mode", async () => {
    renderWith(ALPHA_CONFIG, <AvatarMenu user={user} onSignOut={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Account menu" }));
    expect(screen.queryByRole("menuitem", { name: "My scenarios" })).toBeNull();
    expect(screen.queryByRole("menuitem", { name: "Creator stats" })).toBeNull();
    expect(screen.getByRole("menuitem", { name: "Settings" })).toBeInTheDocument();
  });
});
