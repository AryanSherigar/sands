import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { InvitePage } from "../InvitePage";

const renderInvite = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/invite/abc123"]}>
        <Routes>
          <Route path="/invite/:token" element={<InvitePage />} />
          <Route path="/scenario/:id" element={<p>Story page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

describe("InvitePage", () => {
  it("accepts the invite once and sends the user to the story's page", async () => {
    let acceptCalls = 0;
    server.use(
      http.post("*/v1/invites/abc123/accept", () => {
        acceptCalls += 1;
        return HttpResponse.json({ scenario_id: "story-9" });
      }),
    );
    renderInvite();

    expect(await screen.findByText("Story page")).toBeInTheDocument();
    expect(acceptCalls).toBe(1);
  });

  it("says an unknown link is not valid", async () => {
    server.use(
      http.post("*/v1/invites/abc123/accept", () =>
        HttpResponse.json({ detail: "invalid" }, { status: 404 }),
      ),
    );
    renderInvite();

    expect(await screen.findByRole("alert")).toHaveTextContent("This invite link isn't valid.");
    expect(screen.getByRole("link", { name: "Browse stories" })).toHaveAttribute("href", "/discover");
  });

  it("says a used or expired link needs a new one", async () => {
    server.use(
      http.post("*/v1/invites/abc123/accept", () =>
        HttpResponse.json({ detail: "gone" }, { status: 410 }),
      ),
    );
    renderInvite();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This invite link has already been used or has expired. Ask the owner for a new one.",
    );
  });

  it("falls back to a plain message for any other failure", async () => {
    server.use(
      http.post("*/v1/invites/abc123/accept", () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
    );
    renderInvite();

    expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't open this invite. Try again in a moment.");
  });
});
