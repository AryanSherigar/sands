import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { MasterModeCreateFlow } from "./MasterModeCreateFlow";

const API_URL = "http://localhost:8000";

describe("MasterModeCreateFlow", () => {
  it("creates the master scenario as public so it keeps its old publishing behaviour", async () => {
    const posts: Array<Record<string, unknown>> = [];
    server.use(
      http.post(`${API_URL}/v1/scenarios`, async ({ request }) => {
        posts.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json({ scenario_id: "scenario-9" }, { status: 201 });
      }),
    );
    render(
      <MemoryRouter>
        <QueryClientProvider client={new QueryClient()}>
          <MasterModeCreateFlow />
        </QueryClientProvider>
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText("Scenario title"), "The Keep");
    await userEvent.click(screen.getByRole("button", { name: /create master-mode scenario/i }));

    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0]).toMatchObject({ title: "The Keep", mode: "master", visibility: "public" });
  });
});
