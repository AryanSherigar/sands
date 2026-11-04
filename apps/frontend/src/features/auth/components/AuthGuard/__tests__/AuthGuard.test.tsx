import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { createQueryWrapper } from "@/test/queryWrapper";
import { useAuthStore } from "../../../stores/auth.store";
import { AuthGuard } from "../AuthGuard";

const renderGuard = (): void => {
  const Wrapper = createQueryWrapper();
  render(
    <Wrapper>
      <MemoryRouter initialEntries={["/secret"]}>
        <Routes>
          <Route
            path="/secret"
            element={
              <AuthGuard>
                <p>secret content</p>
              </AuthGuard>
            }
          />
          <Route path="/login" element={<p>login page</p>} />
        </Routes>
      </MemoryRouter>
    </Wrapper>,
  );
};

const signIn = (): void => {
  useAuthStore.setState({
    accessToken: "token",
    isAuthenticated: true,
    isLoading: false,
    user: { user_id: "u1", display_name: "T", onboarding_completed: true },
  });
};

describe("AuthGuard", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
  });

  it("redirects a signed-out visitor to login", async () => {
    renderGuard();
    expect(await screen.findByText("login page")).toBeInTheDocument();
  });

  it("shows the page to a signed-in user", async () => {
    signIn();
    renderGuard();
    expect(await screen.findByText("secret content")).toBeInTheDocument();
  });
});
