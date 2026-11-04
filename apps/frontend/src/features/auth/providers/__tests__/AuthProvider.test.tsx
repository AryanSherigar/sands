import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useAuthStore } from "../../stores/auth.store";
import { AuthProvider } from "../AuthProvider";

describe("AuthProvider", () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, accessToken: null, isAuthenticated: false, isLoading: true });
    server.use(
      http.post(
        "*/v1/auth/refresh",
        () => new HttpResponse(null, { status: 401 }),
      ),
    );
  });

  it("renders its children and finishes loading when the silent refresh is refused", async () => {
    render(
      <AuthProvider>
        <p>app</p>
      </AuthProvider>,
    );

    expect(await screen.findByText("app")).toBeInTheDocument();
    await waitFor(() => expect(useAuthStore.getState().isLoading).toBe(false));
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});
