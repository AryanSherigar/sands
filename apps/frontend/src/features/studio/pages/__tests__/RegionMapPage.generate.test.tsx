import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import { RegionMapPage } from "../RegionMapPage";

vi.mock("../../components/RegionMapEditor/RegionMapEditor", () => ({
  RegionMapEditor: (props: { pictureUrl: string; startFile?: File | null }) => (
    <div data-testid="editor" data-picture={props.pictureUrl} data-start={props.startFile?.name ?? ""} />
  ),
}));

const SCENARIO_ID = "scenario-1";
const REGION_URL = "https://cdn.example/scenario-maps/regions.png";
const ART_URL = "https://cdn.example/scenario-maps/art.webp";
const SIZE = { width: 1792, height: 1344 };

function useGenerationHandlers(isArtFailing: boolean): void {
  server.use(
    http.post(`*/v1/scenarios/${SCENARIO_ID}/strategy-map/generate-regions`, () =>
      HttpResponse.json({ region_image_url: REGION_URL, ...SIZE }),
    ),
    http.get(REGION_URL, () => new HttpResponse(new Uint8Array([1, 2, 3]), { headers: { "Content-Type": "image/png" } })),
    http.post(`*/v1/scenarios/${SCENARIO_ID}/strategy-map/generate-art`, () =>
      isArtFailing
        ? HttpResponse.json({ detail: "down" }, { status: 502 })
        : HttpResponse.json({ picture_url: ART_URL, ...SIZE }),
    ),
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
  it("generates a map and opens the editor with the art and the region image", async () => {
    useGenerationHandlers(false);
    renderPage();
    await generateFromDescription("a desert empire");
    const editor = await screen.findByTestId("editor");
    expect(editor).toHaveAttribute("data-picture", ART_URL);
    expect(editor).toHaveAttribute("data-start", "generated-regions.png");
  });

  it("falls back to the region colors with a notice when the art step fails", async () => {
    useGenerationHandlers(true);
    renderPage();
    await generateFromDescription("a desert empire");
    expect(await screen.findByTestId("editor")).toHaveAttribute("data-picture", REGION_URL);
    expect(screen.getByText(/The painted picture failed, showing the region colors\./)).toBeInTheDocument();
  });

  it("returns to the form with the description kept when choosing a different picture", async () => {
    useGenerationHandlers(false);
    renderPage();
    await generateFromDescription("a desert empire");
    await screen.findByTestId("editor");
    await userEvent.setup().click(screen.getByRole("button", { name: /choose a different picture/i }));
    expect(screen.getByLabelText(/describe your world/i)).toHaveValue("a desert empire");
  });

  it("keeps Generate disabled until the description has three characters", async () => {
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
