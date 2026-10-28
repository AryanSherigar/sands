import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import {
  ALPHA_CONFIG,
  NON_ALPHA_CONFIG,
  alphaConfigHandler,
} from "@/test/alphaFixtures";
import { createQueryWrapper } from "@/test/queryWrapper";
import { useAuthStore } from "../../../stores/auth.store";
import { AuthGuard } from "../AuthGuard";

const consentStatusHandler = (isCurrent: boolean) =>
  http.get("*/v1/users/me", () =>
    HttpResponse.json({ alpha_consent_is_current: isCurrent }),
  );

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
    server.use(alphaConfigHandler(NON_ALPHA_CONFIG));
    renderGuard();
    expect(await screen.findByText("login page")).toBeInTheDocument();
  });

  it("shows the page to a signed-in user when alpha mode is off", async () => {
    server.use(alphaConfigHandler(NON_ALPHA_CONFIG));
    signIn();
    renderGuard();
    expect(await screen.findByText("secret content")).toBeInTheDocument();
  });

  it("shows the page when the alpha consent is current", async () => {
    server.use(alphaConfigHandler(ALPHA_CONFIG), consentStatusHandler(true));
    signIn();
    renderGuard();
    expect(await screen.findByText("secret content")).toBeInTheDocument();
  });

  it("blocks the page behind the re-consent screen until accepted", async () => {
    let isCurrent = false;
    server.use(
      alphaConfigHandler(ALPHA_CONFIG),
      http.get("*/v1/users/me", () =>
        HttpResponse.json({ alpha_consent_is_current: isCurrent }),
      ),
      http.post("*/v1/users/me/alpha-consent", () => {
        isCurrent = true;
        return HttpResponse.json({ alpha_consent_is_current: true });
      }),
    );
    signIn();
    renderGuard();

    const acceptButton = await screen.findByRole("button", {
      name: /i accept/i,
    });
    expect(screen.queryByText("secret content")).toBeNull();
    await userEvent.click(acceptButton);

    expect(await screen.findByText("secret content")).toBeInTheDocument();
  });

  it("lets the page through when the consent status cannot be read", async () => {
    server.use(
      alphaConfigHandler(ALPHA_CONFIG),
      http.get("*/v1/users/me", () => new HttpResponse(null, { status: 500 })),
    );
    signIn();
    renderGuard();
    expect(await screen.findByText("secret content")).toBeInTheDocument();
  });
});
