import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { ScenarioMetaForm } from "./ScenarioMetaForm";

const API_URL = "http://localhost:8000";
const SCENARIO_ID = "scenario-1";

const renderForm = (): void => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <ScenarioMetaForm scenarioId={SCENARIO_ID} />
    </QueryClientProvider>,
  );
};

describe("ScenarioMetaForm", () => {
  it("edits the title and saves the updated metadata", async () => {
    let savedPayload: unknown = null;
    server.use(
      http.get(`${API_URL}/v1/scenarios/${SCENARIO_ID}`, () =>
        HttpResponse.json({
          scenario_id: SCENARIO_ID,
          title: "The Hollow Cairn",
          logline: "A dungeon of forgotten kings.",
          genre_tags: [],
          complexity_tier: "master",
          content_tag: "teen",
          player_count_support: "solo",
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
    renderForm();

    const titleInput = await screen.findByDisplayValue("The Hollow Cairn");
    await user.clear(titleInput);
    await user.type(titleInput, "The Deeper Cairn");

    await user.click(screen.getByRole("button", { name: /^save$/i }));

    const payload = savedPayload as { title: string };
    expect(payload.title).toBe("The Deeper Cairn");
  });

  it("loads and saves cover image url updates", async () => {
    let savedPayload: unknown = null;
    server.use(
      http.get(`${API_URL}/v1/scenarios/${SCENARIO_ID}`, () =>
        HttpResponse.json({
          scenario_id: SCENARIO_ID,
          title: "The Hollow Cairn",
          logline: "A dungeon of forgotten kings.",
          genre_tags: [],
          complexity_tier: "master",
          content_tag: "teen",
          player_count_support: "solo",
          cover_image_url:
            "http://localhost:8000/uploads/scenario-covers/old.png",
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
    renderForm();

    const preview = await screen.findByAltText("Scenario cover preview");
    expect(preview).toHaveAttribute(
      "src",
      "http://localhost:8000/uploads/scenario-covers/old.png",
    );

    const removeBtn = screen.getByRole("button", { name: /remove image/i });
    await user.click(removeBtn);

    await user.click(screen.getByRole("button", { name: /^save$/i }));

    const payload = savedPayload as Record<string, unknown>;
    expect(payload.cover_image_url).toBeUndefined();
  });

  it("immediately saves cover image url when image is uploaded", async () => {
    let savedPayload: unknown = null;
    server.use(
      http.get(`${API_URL}/v1/scenarios/${SCENARIO_ID}`, () =>
        HttpResponse.json({
          scenario_id: SCENARIO_ID,
          title: "The Hollow Cairn",
          logline: "A dungeon of forgotten kings.",
          genre_tags: [],
          complexity_tier: "master",
          content_tag: "teen",
          player_count_support: "solo",
          cover_image_url: null,
        }),
      ),
      http.post(`${API_URL}/v1/uploads/scenario-cover-image`, () =>
        HttpResponse.json({
          url: "http://localhost:8000/uploads/new-cover.png",
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
    renderForm();

    const file = new File(["dummy content"], "cover.png", {
      type: "image/png",
    });
    const input = await screen.findByLabelText(/^cover image$/i);
    await user.upload(input, file);

    await screen.findByAltText("Scenario cover preview");
    const payload = savedPayload as { cover_image_url?: string };
    expect(payload.cover_image_url).toBe(
      "http://localhost:8000/uploads/new-cover.png",
    );
  });

  it("saves the chosen themes alongside the other metadata", async () => {
    let savedPayload: unknown = null;
    server.use(
      http.get(`${API_URL}/v1/scenarios/${SCENARIO_ID}`, () =>
        HttpResponse.json({
          scenario_id: SCENARIO_ID,
          title: "The Hollow Cairn",
          logline: "A dungeon of forgotten kings.",
          genre_tags: [],
          complexity_tier: "master",
          content_tag: "teen",
          content_tags: ["romance"],
          player_count_support: "solo",
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
    renderForm();

    expect(
      await screen.findByRole("button", { name: "Romance", pressed: true }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Moral ambiguity" }));
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    const payload = savedPayload as { content_tags: string[]; content_tag: string };
    expect(payload.content_tags).toEqual(["romance", "moral-ambiguity"]);
    expect(payload.content_tag).toBe("teen");
  });

  it("treats a scenario from an older API without content_tags as having none", async () => {
    server.use(
      http.get(`${API_URL}/v1/scenarios/${SCENARIO_ID}`, () =>
        HttpResponse.json({
          scenario_id: SCENARIO_ID,
          title: "Old Story",
          logline: "",
          genre_tags: [],
          complexity_tier: "newbie",
          content_tag: null,
          player_count_support: "solo",
        }),
      ),
    );

    renderForm();

    expect(await screen.findByText("0 / 5")).toBeInTheDocument();
  });
});
