import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import type { MapGenerationJob } from "../../types/mapGeneration.types";
import { RegionMapPage } from "../RegionMapPage";

vi.mock("../../components/RegionMapEditor/RegionMapEditor", () => ({
  RegionMapEditor: (props: { pictureUrl: string; startFile?: File | null }) => (
    <div data-testid="editor" data-picture={props.pictureUrl} data-start={props.startFile?.name ?? ""} />
  ),
}));

const SCENARIO_ID = "scenario-1";
const REGION_URL = "https://cdn.example/scenario-maps/regions.png";
const ART_URL = "https://cdn.example/scenario-maps/art.webp";
const POLL_WAIT_MS = 6000;

const buildJob = (overrides: Partial<MapGenerationJob>): MapGenerationJob => ({
  job_id: "job-1",
  scenario_id: SCENARIO_ID,
  status: "succeeded",
  description: "a desert empire",
  region_image_url: REGION_URL,
  picture_url: ART_URL,
  width: 1792,
  height: 1344,
  has_art: true,
  error_message: null,
  created_at: "2026-11-04T00:00:00Z",
  updated_at: "2026-11-04T00:00:00Z",
  ...overrides,
});

function useJobHandlers(options: { startedJob?: Partial<MapGenerationJob>; latest: MapGenerationJob | null }): void {
  let hasStarted = false;
  server.use(
    http.post(`*/v1/scenarios/${SCENARIO_ID}/strategy-map/generate`, () => {
      hasStarted = true;
      return HttpResponse.json(buildJob({ status: "pending", region_image_url: null, picture_url: null }), {
        status: 202,
      });
    }),
    http.get(`*/v1/scenarios/${SCENARIO_ID}/strategy-map/jobs/latest`, () => {
      const job = hasStarted ? buildJob(options.startedJob ?? {}) : options.latest;
      return job ? HttpResponse.json(job) : HttpResponse.json({ detail: "none" }, { status: 404 });
    }),
    http.get(REGION_URL, () => new HttpResponse(new Uint8Array([1, 2, 3]), { headers: { "Content-Type": "image/png" } })),
  );
}

function renderPage(): void {
  const Wrapper = createQueryWrapper();
  render(
    <Wrapper>
      <MemoryRouter initialEntries={[`/studio/${SCENARIO_ID}/map`]}>
        <Routes>
          <Route path="/studio/:id/map" element={<RegionMapPage />} />
        </Routes>
      </MemoryRouter>
    </Wrapper>,
  );
}

async function generateFromDescription(description: string): Promise<void> {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText(/describe your world/i), description);
  await user.click(screen.getByRole("button", { name: "Generate map" }));
}

describe("RegionMapPage generate flow", () => {
  it("starts a background job and opens the editor with the art and region image when it finishes", async () => {
    useJobHandlers({ latest: null });
    renderPage();
    await generateFromDescription("a desert empire");
    expect(await screen.findByText(/generating your map in the background/i)).toBeInTheDocument();
    const editor = await screen.findByTestId("editor", {}, { timeout: POLL_WAIT_MS });
    expect(editor).toHaveAttribute("data-picture", ART_URL);
    expect(editor).toHaveAttribute("data-start", "generated-regions.png");
  });

  it("falls back to the region colors with a notice when the job has no painted art", async () => {
    useJobHandlers({ latest: null, startedJob: { picture_url: null, has_art: false } });
    renderPage();
    await generateFromDescription("a desert empire");
    expect(await screen.findByTestId("editor", {}, { timeout: POLL_WAIT_MS })).toHaveAttribute(
      "data-picture",
      REGION_URL,
    );
    expect(screen.getByText(/The painted picture failed, showing the region colors\./)).toBeInTheDocument();
  });

  it("offers a finished job from before the page was opened instead of opening it silently", async () => {
    useJobHandlers({ latest: buildJob({}) });
    renderPage();
    const useButton = await screen.findByRole("button", { name: "Use this map" });
    expect(screen.queryByTestId("editor")).not.toBeInTheDocument();
    await userEvent.setup().click(useButton);
    expect(await screen.findByTestId("editor")).toHaveAttribute("data-picture", ART_URL);
  });

  it("shows the form as busy with a way back while a job is running", async () => {
    useJobHandlers({ latest: buildJob({ status: "running", region_image_url: null, picture_url: null }) });
    renderPage();
    expect(await screen.findByText(/generating your map in the background/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate map" })).toBeDisabled();
    expect(screen.getByRole("link", { name: /back to the scenario/i })).toHaveAttribute("href", `/studio/${SCENARIO_ID}/edit`);
  });

  it("shows the job's error when the last generation failed", async () => {
    useJobHandlers({ latest: buildJob({ status: "failed", error_message: "Image generation is temporarily unavailable" }) });
    renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent("Image generation is temporarily unavailable");
  });

  it("returns to the form with the description kept when choosing a different picture", async () => {
    useJobHandlers({ latest: null });
    renderPage();
    await generateFromDescription("a desert empire");
    await screen.findByTestId("editor", {}, { timeout: POLL_WAIT_MS });
    await userEvent.setup().click(screen.getByRole("button", { name: /choose a different picture/i }));
    expect(screen.getByLabelText(/describe your world/i)).toHaveValue("a desert empire");
  });

  it("keeps Generate disabled until the description has three characters", async () => {
    useJobHandlers({ latest: null });
    renderPage();
    const user = userEvent.setup();
    const button = screen.getByRole("button", { name: "Generate map" });
    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText(/describe your world/i), "ab");
    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText(/describe your world/i), "c");
    expect(button).toBeEnabled();
  });
});
