import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { MinigameEditor } from "../MinigameEditor";

const BASE = "http://localhost:8000/v1/scenarios/scenario-1";

const mockScenario = (enabledTools: string[]): void => {
  server.use(
    http.get(BASE, () =>
      HttpResponse.json({
        scenario_id: "scenario-1",
        enabled_tools: enabledTools,
        state_schema: { sanity: { type: "number", label: "Sanity" } },
      }),
    ),
    http.get(`${BASE}/entities`, () => HttpResponse.json({ items: [] })),
    http.get(`${BASE}/minigames`, () => HttpResponse.json({ items: [] })),
  );
};

const renderEditor = (): void => {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MinigameEditor scenarioId="scenario-1" />
    </QueryClientProvider>,
  );
};

describe("Composure minigame authoring", () => {
  it("explains that the Composure tool must be turned on first", async () => {
    mockScenario([]);
    const user = userEvent.setup();
    renderEditor();
    await user.click(await screen.findByRole("button", { name: /new minigame/i }));

    expect(
      screen.getByRole("option", { name: /turn on the composure tool first/i }),
    ).toBeInTheDocument();
  });

  it("saves a composure config and outcome lists with several mutations", async () => {
    mockScenario(["composure"]);
    let captured: Record<string, unknown> | null = null;
    server.use(
      http.post(`${BASE}/minigames`, async ({ request }) => {
        captured = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ minigame_id: "m1", scenario_id: "scenario-1", ...captured });
      }),
    );
    const user = userEvent.setup();
    renderEditor();
    await user.click(await screen.findByRole("button", { name: /new minigame/i }));

    await user.type(screen.getByLabelText(/^label$/i), "The Hum");
    await user.selectOptions(screen.getByLabelText("Minigame type"), "rhythm_composure");
    await user.clear(screen.getByLabelText("Tempo (beats per minute)"));
    await user.type(screen.getByLabelText("Tempo (beats per minute)"), "66");
    await user.selectOptions(screen.getByLabelText("Sound profile"), "chase");

    const paths = screen.getAllByLabelText(/mutation 1 path/i);
    await user.type(paths[0], "sanity");
    await user.type(paths[1], "sanity");
    await user.click(screen.getAllByRole("button", { name: /add mutation/i })[0]);
    await user.type(screen.getByLabelText(/mutation 2 path/i), "flags.won");
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    expect(captured).toMatchObject({
      minigame_type: "rhythm_composure",
      composure_config: { target_bpm: 66, audio_profile: "chase", keys: ["W", "A", "S", "D"] },
      lose_mutations: [{ path: "sanity" }],
    });
    expect((captured as unknown as { win_mutations: unknown[] }).win_mutations).toHaveLength(2);
    expect((captured as unknown as { lock?: unknown }).lock).toBeUndefined();
  });

  it("keeps at least one key selected", async () => {
    mockScenario(["composure"]);
    const user = userEvent.setup();
    renderEditor();
    await user.click(await screen.findByRole("button", { name: /new minigame/i }));
    await user.selectOptions(screen.getByLabelText("Minigame type"), "rhythm_composure");

    for (const key of ["W", "A", "S"]) {
      await user.click(screen.getByLabelText(`Key ${key}`));
    }
    await user.click(screen.getByLabelText("Key D"));

    expect(screen.getByLabelText("Key D")).toBeChecked();
  });
});
