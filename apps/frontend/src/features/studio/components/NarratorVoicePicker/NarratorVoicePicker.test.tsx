import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { NarratorVoicePicker } from "./NarratorVoicePicker";

const API_URL = "http://localhost:8000";
const SCENARIO_ID = "scenario-1";

const renderPicker = (): void => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <NarratorVoicePicker scenarioId={SCENARIO_ID} />
    </QueryClientProvider>,
  );
};

describe("NarratorVoicePicker", () => {
  it("saves immediately when a new voice is selected", async () => {
    let savedPayload: unknown = null;
    server.use(
      http.get(`${API_URL}/v1/scenarios/${SCENARIO_ID}`, () =>
        HttpResponse.json({
          scenario_id: SCENARIO_ID,
          narrator_voice_name: "Kore",
        }),
      ),
      http.patch(
        `${API_URL}/v1/scenarios/${SCENARIO_ID}`,
        async ({ request }) => {
          savedPayload = await request.json();
          return HttpResponse.json({
            scenario_id: SCENARIO_ID,
            ...(savedPayload as Record<string, unknown>),
          });
        },
      ),
    );

    const user = userEvent.setup();
    renderPicker();

    const select = await screen.findByLabelText(/narrator voice/i);
    await user.selectOptions(select, "Puck");

    expect(savedPayload).toEqual({ narrator_voice_name: "Puck" });
  });

  it("falls back to the default voice when the scenario has none set", async () => {
    server.use(
      http.get(`${API_URL}/v1/scenarios/${SCENARIO_ID}`, () =>
        HttpResponse.json({
          scenario_id: SCENARIO_ID,
          narrator_voice_name: null,
        }),
      ),
    );

    renderPicker();
    const select = (await screen.findByLabelText(
      /narrator voice/i,
    )) as HTMLSelectElement;
    expect(select.value).toBe("Kore");
  });
});
