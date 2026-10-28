import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { HudEditor } from "./HudEditor";

const BASE = "http://localhost:8000/v1/scenarios/scenario-1";

const schemaWith = (extra: Record<string, unknown> = {}) => ({
  scenario_id: "scenario-1",
  state_schema: {
    shift_minutes: { type: "number", label: "Shift minutes", initial: 0, ...extra },
    sanity: {
      type: "number",
      label: "Sanity",
      initial: 85,
      display: {
        kind: "meter",
        label: "Sanity",
        clamp_min: 0,
        clamp_max: 100,
        tiers: [{ name: "Clear", min: 75 }, { name: "Low" }],
      },
    },
    tension: { type: "enum", label: "Tension", options: ["calm", "tense"], initial: "calm" },
  },
});

const renderEditor = (): void => {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <HudEditor scenarioId="scenario-1" />
    </QueryClientProvider>,
  );
};

describe("HudEditor", () => {
  it("writes a clock hint back into the state schema", async () => {
    let saved: { state_schema: Record<string, { display?: unknown }> } | null = null;
    server.use(
      http.get(BASE, () => HttpResponse.json(schemaWith())),
      http.patch(BASE, async ({ request }) => {
        saved = (await request.json()) as typeof saved;
        return HttpResponse.json({ ...schemaWith(), ...saved });
      }),
    );
    const user = userEvent.setup();
    renderEditor();

    await screen.findAllByRole("option", { name: /shift minutes/i });
    await user.selectOptions(screen.getByLabelText("Clock value"), "shift_minutes");
    await user.click(screen.getByRole("button", { name: /save clock/i }));

    expect(saved!.state_schema.shift_minutes.display).toMatchObject({
      kind: "clock",
      start: "23:00",
      format: "12h",
    });
    expect(saved!.state_schema.sanity).toBeDefined();
  });

  it("refuses a bad start time and keeps Save disabled", async () => {
    server.use(http.get(BASE, () => HttpResponse.json(schemaWith())));
    const user = userEvent.setup();
    renderEditor();

    await screen.findAllByRole("option", { name: /shift minutes/i });
    await user.selectOptions(screen.getByLabelText("Clock value"), "shift_minutes");
    await user.clear(screen.getByLabelText("Clock start time"));
    await user.type(screen.getByLabelText("Clock start time"), "25:99");

    expect(screen.getByText(/written HH:MM/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save clock/i })).toBeDisabled();
  });

  it("previews the meter tier at the slider position", async () => {
    server.use(http.get(BASE, () => HttpResponse.json(schemaWith())));
    renderEditor();

    const slider = await screen.findByLabelText("Preview Sanity");
    fireEvent.change(slider, { target: { value: "30" } });

    expect(screen.getByLabelText("Preview Sanity")).toHaveValue("30");
    expect(await screen.findByText(/low/i)).toBeInTheDocument();
  });

  it("removes a hint", async () => {
    let saved: { state_schema: Record<string, Record<string, unknown>> } | null = null;
    server.use(
      http.get(BASE, () => HttpResponse.json(schemaWith())),
      http.patch(BASE, async ({ request }) => {
        saved = (await request.json()) as typeof saved;
        return HttpResponse.json({ ...schemaWith(), ...saved });
      }),
    );
    const user = userEvent.setup();
    renderEditor();

    await user.click(await screen.findByRole("button", { name: /remove meter/i }));

    expect("display" in saved!.state_schema.sanity).toBe(false);
  });
});
