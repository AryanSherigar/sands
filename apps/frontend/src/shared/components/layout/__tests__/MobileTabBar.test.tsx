import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { useSignInModalStore } from "@/shared/stores/signInModal.store";
import { MobileTabBar } from "../MobileTabBar";

vi.mock("@/shared/hooks/useIsAlphaMode", () => ({
  useIsAlphaMode: () => false,
}));

const mockUser = vi.hoisted(() => ({ current: null as object | null }));
vi.mock("@/features/auth/hooks/useAuth", () => ({
  useAuth: () => ({ user: mockUser.current }),
}));

const renderBar = (): void => {
  render(
    <MemoryRouter initialEntries={["/discover"]}>
      <MobileTabBar />
      <Routes>
        <Route path="/discover" element={<p>discover page</p>} />
        <Route path="/studio/new" element={<p>new story page</p>} />
        <Route path="/login" element={<p>login page</p>} />
      </Routes>
    </MemoryRouter>,
  );
};

describe("MobileTabBar signed out", () => {
  beforeEach(() => {
    mockUser.current = null;
    useAuthStore.setState({ isAuthenticated: false });
    useSignInModalStore.setState({ trigger: null, resolvePending: null });
  });

  it("opens the sign-in modal in place from the Sign in tab", async () => {
    renderBar();
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(useSignInModalStore.getState().trigger).toBe("mobile-tab");
    expect(screen.getByText("discover page")).toBeInTheDocument();
  });

  it("opens the create modal from Studio and continues to /studio/new after sign-in", async () => {
    renderBar();
    await userEvent.click(screen.getByRole("button", { name: "Studio" }));
    expect(useSignInModalStore.getState().trigger).toBe("create");
    act(() => useSignInModalStore.getState().settle(true));
    expect(await screen.findByText("new story page")).toBeInTheDocument();
  });

  it("stays put when the create modal is dismissed", async () => {
    renderBar();
    await userEvent.click(screen.getByRole("button", { name: "Studio" }));
    act(() => useSignInModalStore.getState().settle(false));
    expect(screen.getByText("discover page")).toBeInTheDocument();
  });
});

describe("MobileTabBar signed in", () => {
  it("keeps Studio and Profile as plain links", () => {
    mockUser.current = { user_id: "u1" };
    renderBar();
    expect(screen.getByRole("link", { name: "Studio" })).toHaveAttribute("href", "/studio");
    expect(screen.getByRole("link", { name: "Profile" })).toHaveAttribute("href", "/profile");
  });
});
