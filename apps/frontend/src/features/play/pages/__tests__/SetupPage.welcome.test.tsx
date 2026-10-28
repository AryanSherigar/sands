import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { server } from "@/test/msw/server";
import { saveWelcomeHandoff } from "../../utils/welcomeHandoff";
import { SetupPage } from "../SetupPage";

const API = "http://localhost:8000/v1";
const SCENARIO = {
  scenario_id: "night-desk", title: "Night Desk", genre_tags: [],
  world_data: { presentation: { welcome_tape_id: "tallis-v1" } },
  setup_schema: [{ key: "character_name", label: "Your name", is_character_name: true }],
};

class LoadingAudioContext {
  destination = {};
  state = "suspended";
  createGain() { return { gain: { value: 1 }, connect: vi.fn() }; }
  createAnalyser() { return { connect: vi.fn() }; }
  async close() { this.state = "closed"; }
}

function renderSetup(path = "/setup/night-desk") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><Routes>
    <Route path="/setup/:id" element={<SetupPage />} />
    <Route path="/play/:id" element={<p>Existing story</p>} />
  </Routes></MemoryRouter></QueryClientProvider>);
}

beforeEach(() => {
  sessionStorage.clear(); vi.stubGlobal("AudioContext", LoadingAudioContext);
  useAuthStore.setState({ accessToken: "token", isAuthenticated: true, isLoading: false,
    user: { user_id: "owner", display_name: "Ayla", onboarding_completed: true, show_mature: false } });
  server.use(http.get(`${API}/scenarios/night-desk`, () => HttpResponse.json(SCENARIO)),
    http.get(`${API}/scenarios/night-desk/reviews`, () => HttpResponse.json({ items: [], total_count: 0 })),
    http.get("*/welcome-tapes/tallis-v1/*", () => new HttpResponse(null, { status: 503 })));
});

afterEach(() => { cleanup(); sessionStorage.clear(); vi.unstubAllGlobals(); });

describe("Night Desk setup handoff", () => {
  it("waits for creation after Skip and never requests voice", async () => {
    let finishCreation: (() => void) | undefined;
    let voiceRequests = 0;
    server.use(http.post(`${API}/playthroughs`, async () => {
      await new Promise<void>(resolve => { finishCreation = resolve; });
      return HttpResponse.json({ playthrough_id: "run-1" }, { status: 201 });
    }), http.post("http://localhost:8001/v1/voice/welcome/*", () => {
      voiceRequests += 1; return new HttpResponse(null, { status: 502 });
    }));
    renderSetup(); const user = userEvent.setup();
    await user.type(await screen.findByRole("textbox"), "Alex");
    await user.click(screen.getByRole("button", { name: /start adventure/i }));
    await user.click(await screen.findByRole("button", { name: /skip tape|continue to story/i }));
    expect(screen.queryByText("Existing story")).not.toBeInTheDocument();
    await waitFor(() => expect(finishCreation).toBeDefined());
    finishCreation?.();
    expect(await screen.findByText("Existing story")).toBeVisible();
    expect(voiceRequests).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it("reloads into the existing run without creating another", async () => {
    let creations = 0;
    server.use(http.post(`${API}/playthroughs`, () => { creations += 1; return HttpResponse.json({}); }));
    saveWelcomeHandoff("night-desk", "run-1");
    renderSetup();
    expect(await screen.findByText("Existing story")).toBeVisible();
    expect(creations).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });
});
