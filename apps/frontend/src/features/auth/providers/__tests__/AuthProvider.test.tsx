import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { clearInvite, readInvite } from "../../lib/inviteStorage";
import { AuthProvider } from "../AuthProvider";

describe("AuthProvider invite capture", () => {
  beforeEach(() => {
    clearInvite();
    server.use(
      http.post(
        "*/v1/auth/refresh",
        () => new HttpResponse(null, { status: 401 }),
      ),
    );
  });

  it("captures ?invite= from the landing URL on mount", async () => {
    window.history.pushState({}, "", "/?invite=landing-code");

    render(
      <AuthProvider>
        <p>app</p>
      </AuthProvider>,
    );

    expect(await screen.findByText("app")).toBeInTheDocument();
    expect(readInvite()).toBe("landing-code");
    window.history.pushState({}, "", "/");
  });
});
