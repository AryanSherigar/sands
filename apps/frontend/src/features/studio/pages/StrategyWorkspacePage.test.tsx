import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import type { ScenarioResponse } from "../types/scenario.types";
import { StrategyWorkspacePage } from "./StrategyWorkspacePage";

const REGION = {
  id: "north",
  name: "North Reach",
  terrain: "plain",
  outline: "M0 0",
  label_point: { x: 1, y: 1 },
  neighbor_ids: [],
  source_color: null,
  source_ref: null,
};

const SCENARIO = {
  scenario_id: "scenario-1",
  title: "The Reach",
  mode: "strategy",
  status: "draft",
  content_tag: null,
  content_edited_at: "2026-10-27T00:00:00Z",
  strategy_document: {},
} as unknown as ScenarioResponse;

const renderPage = (): void => {
  const Wrapper = createQueryWrapper();
  render(
    <Wrapper>
      <MemoryRouter>
        <StrategyWorkspacePage scenario={SCENARIO} />
      </MemoryRouter>
    </Wrapper>,
  );
};

describe("StrategyWorkspacePage", () => {
  it("shows the server's blocking issues and keeps Publish disabled", async () => {
    server.use(
      http.get("*/v1/scenarios/scenario-1/strategy-map", () =>
        HttpResponse.json({ regions: [REGION] }),
      ),
      http.post("*/v1/scenarios/scenario-1/strategy-check", () =>
        HttpResponse.json({
          blocking: [{ code: "no_playable_faction", path: "factions", message: "no playable faction" }],
          warnings: [],
        }),
      ),
    );

    renderPage();

    expect(await screen.findByText("no playable faction")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Publish" })).toBeDisabled();
  });

  it("adds a faction with a leader and saves the document", async () => {
    let saved: { strategy_document: { factions: { name: string }[] } } | null = null;
    server.use(
      http.get("*/v1/scenarios/scenario-1/strategy-map", () =>
        HttpResponse.json({ regions: [REGION] }),
      ),
      http.post("*/v1/scenarios/scenario-1/strategy-check", () =>
        HttpResponse.json({ blocking: [], warnings: [] }),
      ),
      http.patch("*/v1/scenarios/scenario-1", async ({ request }) => {
        saved = (await request.json()) as typeof saved;
        return HttpResponse.json({ ...SCENARIO, ...saved });
      }),
    );
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("New faction name"), "Ashford");
    await user.click(screen.getByRole("button", { name: "Add faction" }));

    expect(await screen.findByLabelText("Faction name")).toHaveValue("Ashford");
    await waitFor(() => expect(saved?.strategy_document.factions[0].name).toBe("Ashford"));
  });
});
