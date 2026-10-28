import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { MasterModeStudioLayout } from "../../Layout/MasterModeStudioLayout";
import { useStudioStore } from "../../../stores/studio.store";

const API_URL = "http://localhost:8000";
const SCENARIO_ID = "scenario-1";

describe("Minigames tab", () => {
  it("appears in MasterModeStudioLayout and renders MinigameEditor when selected", async () => {
    server.use(
      http.get(`${API_URL}/v1/scenarios/${SCENARIO_ID}`, () =>
        HttpResponse.json({ scenario_id: SCENARIO_ID, state_schema: {} }),
      ),
      http.get(`${API_URL}/v1/scenarios/${SCENARIO_ID}/entities`, () =>
        HttpResponse.json({ items: [] }),
      ),
      http.get(`${API_URL}/v1/scenarios/${SCENARIO_ID}/minigames`, () =>
        HttpResponse.json({ items: [] }),
      ),
    );
    useStudioStore.setState({ activeMasterTab: "minigames" });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <MasterModeStudioLayout scenarioId={SCENARIO_ID} />
        </QueryClientProvider>
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole("button", { name: /^minigames$/i }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: /^minigames$/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /new minigame/i }),
    ).toBeInTheDocument();
  });
});
