import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { GUIDE_TAB_ID, STUDIO_TABS_STORAGE_PREFIX } from "../../constants/studioTabs";
import { useStudioStore } from "../../stores/studio.store";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { renderStudio } from "../../test/renderStudio";
import {
  STUDIO_TEST_SCENARIO_ID,
  buildScenarioFixture,
  installStudioApi,
} from "../../test/studioApiMock";

const EDIT_PATH = `/studio/${STUDIO_TEST_SCENARIO_ID}/edit`;
const WAIT = { timeout: 4000 };
const STARTED = buildScenarioFixture({ title: "The Door Below", logline: "A keeper hears knocking." });

describe("Returning creator", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
    useStudioStore.getState().setHasEditConflict(false);
    useStudioStore.getState().setSaveState(false);
    // @ts-expect-error jsdom has no matchMedia unless a test installs one
    delete window.matchMedia;
  });

  it("opens at the first unfinished step with one quiet welcome line", async () => {
    installStudioApi({ scenario: STARTED });
    renderStudio({ path: EDIT_PATH });

    expect(await screen.findByText("Welcome back. You were working on Premise.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Tell us about your story, the stakes." })).toBeInTheDocument();
  });

  it("drops the welcome line on the first edit", async () => {
    installStudioApi({ scenario: STARTED });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();
    await screen.findByText("Welcome back. You were working on Premise.");

    await user.type(screen.getByRole("textbox", { name: "Your story and the stakes" }), "A war");

    await waitFor(() => expect(screen.queryByText(/Welcome back/)).toBeNull(), WAIT);
  });

  it("restores remembered tabs instead of showing the welcome line", async () => {
    localStorage.setItem(
      `${STUDIO_TABS_STORAGE_PREFIX}${STUDIO_TEST_SCENARIO_ID}`,
      JSON.stringify({ openTabIds: [GUIDE_TAB_ID], activeTabId: GUIDE_TAB_ID, splitTabId: null, guideStep: 3 }),
    );
    installStudioApi({ scenario: STARTED });
    renderStudio({ path: EDIT_PATH });

    expect(await screen.findByRole("heading", { name: "Who will the player be?" })).toBeInTheDocument();
    expect(screen.queryByText(/Welcome back/)).toBeNull();
  });

  it("says nothing for a story with no content yet", async () => {
    installStudioApi({ scenario: buildScenarioFixture() });
    renderStudio({ path: EDIT_PATH });

    await screen.findByRole("heading", { name: "What's your story in one sentence?" });
    expect(screen.queryByText(/Welcome back/)).toBeNull();
  });
});

describe("Live story strip", () => {
  const LIVE = {
    status: "published" as const,
    published_at: "2026-10-27T08:00:00Z",
    content_edited_at: "2026-10-27T08:00:00Z",
  };

  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
    // @ts-expect-error jsdom has no matchMedia unless a test installs one
    delete window.matchMedia;
  });

  it("shows just Live when nothing changed since publishing", async () => {
    installStudioApi({ scenario: buildScenarioFixture({ ...STARTED, ...LIVE }) });
    renderStudio({ path: EDIT_PATH });

    expect(await screen.findByText("Live")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Publish changes" })).toBeInTheDocument();
  });

  it("counts unpublished changes when the story was edited after publishing", async () => {
    installStudioApi({
      scenario: buildScenarioFixture({ ...STARTED, ...LIVE, content_edited_at: "2026-10-27T09:00:00Z" }),
    });
    renderStudio({ path: EDIT_PATH });

    expect(await screen.findByText("Live · 1 unpublished change")).toBeInTheDocument();
  });

  it("adds each saved edit made in this window", async () => {
    let edits = 0;
    installStudioApi({ scenario: buildScenarioFixture({ ...STARTED, ...LIVE }) });
    server.use(
      http.patch("*/v1/scenarios/:scenarioId", async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        edits += 1;
        return HttpResponse.json(
          buildScenarioFixture({
            ...STARTED,
            ...LIVE,
            ...body,
            content_edited_at: `2026-10-27T08:0${edits}:00Z`,
          }),
        );
      }),
    );
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();
    await screen.findByText("Live");

    await user.type(screen.getByLabelText("Story name"), "!");
    expect(await screen.findByText("Live · 1 unpublished change", undefined, WAIT)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Story name"), "?");
    expect(await screen.findByText("Live · 2 unpublished changes", undefined, WAIT)).toBeInTheDocument();
  });
});
