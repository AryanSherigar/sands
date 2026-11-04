import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import type { MapGenerationJob } from "../../../types/mapGeneration.types";
import { MapGenerationStatus } from "../MapGenerationStatus";

const SCENARIO_ID = "scenario-1";

const buildJob = (overrides: Partial<MapGenerationJob>): MapGenerationJob => ({
  job_id: "job-1",
  scenario_id: SCENARIO_ID,
  status: "running",
  description: "a desert empire",
  region_image_url: null,
  picture_url: null,
  width: null,
  height: null,
  has_art: false,
  error_message: null,
  created_at: "2026-11-04T00:00:00Z",
  updated_at: "2026-11-04T00:00:00Z",
  ...overrides,
});

function renderStatus(job: MapGenerationJob | null, hasSavedMap: boolean): { hasLoaded: () => boolean } {
  let hasRequested = false;
  server.use(
    http.get(`*/v1/scenarios/${SCENARIO_ID}/strategy-map/jobs/latest`, () => {
      hasRequested = true;
      return job ? HttpResponse.json(job) : HttpResponse.json({ detail: "none" }, { status: 404 });
    }),
  );
  const Wrapper = createQueryWrapper();
  render(
    <Wrapper>
      <MemoryRouter>
        <MapGenerationStatus scenarioId={SCENARIO_ID} hasSavedMap={hasSavedMap} />
      </MemoryRouter>
    </Wrapper>,
  );
  return { hasLoaded: () => hasRequested };
}

describe("MapGenerationStatus", () => {
  it("says the map is generating in the background while a job runs", async () => {
    renderStatus(buildJob({ status: "running" }), false);
    expect(await screen.findByText(/generating your map in the background/i)).toBeInTheDocument();
  });

  it("links to Map regions when a finished map has not been saved yet", async () => {
    renderStatus(buildJob({ status: "succeeded" }), false);
    expect(await screen.findByRole("link", { name: "Open Map regions" })).toHaveAttribute(
      "href",
      `/studio/${SCENARIO_ID}/region-map`,
    );
  });

  it("stays quiet about a finished job once a map is saved", async () => {
    const { hasLoaded } = renderStatus(buildJob({ status: "succeeded" }), true);
    await waitFor(() => expect(hasLoaded()).toBe(true));
    expect(screen.queryByRole("link", { name: "Open Map regions" })).not.toBeInTheDocument();
  });

  it("shows the failure message with a retry link", async () => {
    renderStatus(buildJob({ status: "failed", error_message: "Image generation is temporarily unavailable" }), false);
    expect(await screen.findByRole("alert")).toHaveTextContent("Image generation is temporarily unavailable");
    expect(screen.getByRole("link", { name: "Try again" })).toBeInTheDocument();
  });

  it("renders nothing when no job exists", async () => {
    const { hasLoaded } = renderStatus(null, false);
    await waitFor(() => expect(hasLoaded()).toBe(true));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
