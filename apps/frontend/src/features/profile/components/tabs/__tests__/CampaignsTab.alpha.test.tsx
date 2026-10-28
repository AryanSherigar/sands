import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { ALPHA_CONFIG, NON_ALPHA_CONFIG } from "@/test/alphaFixtures";
import { createQueryWrapper } from "@/test/queryWrapper";
import type { AlphaConfig } from "@/shared/types/alpha.types";
import { CampaignsTab } from "../CampaignsTab";

const RUN = {
  playthrough_id: "pt-9",
  scenario_id: "sc-1",
  scenario_title: "Night Desk",
  scenario_mode: "master",
  status: "active",
  turn_count: 12,
  cover_image_url: null,
  character_name: null,
  character_archetype: null,
  ended_outcome_title: null,
};

const renderTab = (config: AlphaConfig): void => {
  server.use(
    http.get("*/v1/users/me/playthroughs", () => HttpResponse.json([RUN])),
    http.post("*/v1/playthroughs/pt-9/abandon", () => new HttpResponse(null, { status: 204 })),
  );
  const Wrapper = createQueryWrapper(config);
  render(
    <Wrapper>
      <MemoryRouter>
        <CampaignsTab />
      </MemoryRouter>
    </Wrapper>,
  );
};

const abandonRun = async (): Promise<void> => {
  const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: "Abandon" }));
  await user.click(screen.getByRole("button", { name: "Yes" }));
};

describe("CampaignsTab abandon survey", () => {
  it("asks how the run went after an abandon in alpha mode", async () => {
    renderTab(ALPHA_CONFIG);

    await abandonRun();

    expect(await screen.findByRole("dialog", { name: "How was this run?" })).toBeInTheDocument();
  });

  it("does not ask outside alpha mode", async () => {
    renderTab(NON_ALPHA_CONFIG);

    await abandonRun();

    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });
});
