import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import { AtmosphereEditor } from "./AtmosphereEditor";
import { CueLibrary } from "./CueLibrary";

const BASE = "http://localhost:8000/v1/scenarios/scenario-1";

const scenario = {
  scenario_id: "scenario-1",
  state_schema: {
    sanity: {
      type: "number",
      initial: 85,
      display: { kind: "meter", label: "Sanity", clamp_min: 0, clamp_max: 100 },
    },
    tension: {
      type: "enum",
      options: ["calm", "tense"],
      initial: "calm",
      display: { kind: "tier", label: "Tension" },
    },
  },
};

const wrap = (children: React.ReactNode): void => {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      {children}
    </QueryClientProvider>,
  );
};

describe("AtmosphereEditor", () => {
  it("saves thresholds and intrusive thoughts onto the meter hint", async () => {
    let saved: { state_schema: { sanity: { display: { effects: unknown } } } } | null = null;
    server.use(
      http.get(BASE, () => HttpResponse.json(scenario)),
      http.patch(BASE, async ({ request }) => {
        saved = (await request.json()) as typeof saved;
        return HttpResponse.json({ ...scenario, ...saved });
      }),
    );
    const user = userEvent.setup();
    wrap(<AtmosphereEditor scenarioId="scenario-1" />);

    await user.type(await screen.findByLabelText("Distort words below"), "50");
    await user.type(screen.getByLabelText("Eerie face below"), "25");
    await user.click(screen.getByRole("button", { name: /add intrusive thought/i }));
    await user.type(screen.getByLabelText("Intrusive thought 1"), "don't turn around");
    await user.click(screen.getByRole("button", { name: /save reader effects/i }));

    expect(saved!.state_schema.sanity.display.effects).toEqual({
      moderate_below: 50,
      critical_below: 25,
      intrusive_thoughts: ["don't turn around"],
    });
  });

  it("blocks a critical threshold above the distortion threshold", async () => {
    server.use(http.get(BASE, () => HttpResponse.json(scenario)));
    const user = userEvent.setup();
    wrap(<AtmosphereEditor scenarioId="scenario-1" />);

    await user.type(await screen.findByLabelText("Distort words below"), "20");
    await user.type(screen.getByLabelText("Eerie face below"), "40");

    expect(screen.getByText(/cannot be above/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save reader effects/i })).toBeDisabled();
  });

  it("maps a tension level to a mood", async () => {
    let saved: { state_schema: { tension: { display: { mood_map: unknown } } } } | null = null;
    server.use(
      http.get(BASE, () => HttpResponse.json(scenario)),
      http.patch(BASE, async ({ request }) => {
        saved = (await request.json()) as typeof saved;
        return HttpResponse.json({ ...scenario, ...saved });
      }),
    );
    const user = userEvent.setup();
    wrap(<AtmosphereEditor scenarioId="scenario-1" />);

    await user.selectOptions(await screen.findByLabelText("Music for tense"), "tension");
    await user.click(screen.getByRole("button", { name: /save music/i }));

    expect(saved!.state_schema.tension.display.mood_map).toEqual({ tense: "tension" });
  });
});

describe("CueLibrary", () => {
  it("plays a cue and explains a blocked one", async () => {
    const onPreview = vi.fn().mockResolvedValueOnce("played").mockResolvedValueOnce("blocked");
    const user = userEvent.setup();
    wrap(<CueLibrary onPreview={onPreview} />);

    await user.click(screen.getByRole("button", { name: "Play phone ring" }));
    expect(onPreview).toHaveBeenCalledWith("phone_ring");
    await user.click(screen.getByRole("button", { name: "Play heavy knock" }));

    expect(await screen.findByText(/blocked the sound/i)).toBeInTheDocument();
  });
});
