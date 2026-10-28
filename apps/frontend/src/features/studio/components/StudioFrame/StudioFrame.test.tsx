import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import { GUIDE_TAB_ID, STUDIO_TABS_STORAGE_PREFIX } from "../../constants/studioTabs";
import { buildCardTabId } from "../../lib/studioTabs";
import { useStudioStore } from "../../stores/studio.store";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { buildEntityFixture } from "../../test/cardApiMock";
import { renderStudio } from "../../test/renderStudio";
import {
  STUDIO_TEST_SCENARIO_ID,
  buildScenarioFixture,
  installStudioApi,
} from "../../test/studioApiMock";

const EDIT_PATH = `/studio/${STUDIO_TEST_SCENARIO_ID}/edit`;
const WAIT = { timeout: 4000 };

const mara = buildEntityFixture({ entity_id: "mara", canonical_name: "Mara" });
const tomas = buildEntityFixture({ entity_id: "tomas", canonical_name: "Tomas" });
const lighthouse = buildEntityFixture({
  entity_id: "lighthouse",
  canonical_name: "The Lighthouse",
  entity_type: "location",
});

const setMatchMedia = (isMobile: boolean): void => {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: isMobile && query.includes("max-width"),
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })) as unknown as typeof window.matchMedia;
};

describe("Studio frame", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
    useStudioStore.getState().setHasEditConflict(false);
    // @ts-expect-error jsdom has no matchMedia unless a test installs one
    delete window.matchMedia;
  });

  describe("new story", () => {
    it("opens on the Guide, step 1, with nothing saved until a word is typed", async () => {
      const api = installStudioApi();
      renderStudio({ path: "/studio/new" });

      expect(
        await screen.findByRole("heading", { name: "What's your story in one sentence?" }),
      ).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: "Guide" })).toHaveAttribute("aria-selected", "true");

      const user = userEvent.setup();
      await user.type(screen.getByLabelText("One line idea"), "   ");
      await new Promise((resolve) => setTimeout(resolve, 100));
      expect(api.scenarioCreates).toHaveLength(0);
    });

    it("creates one private newbie draft on the first non-blank character and keeps typing", async () => {
      const api = installStudioApi();
      renderStudio({ path: "/studio/new" });
      const user = userEvent.setup();

      const idea = await screen.findByLabelText("One line idea");
      await user.type(idea, "A lighthouse keeper");

      await waitFor(() => expect(api.scenarioCreates).toHaveLength(1), WAIT);
      expect(api.scenarioCreates[0]).toMatchObject({ mode: "newbie", visibility: "private" });
      await waitFor(() => expect(screen.getByLabelText("One line idea")).toHaveValue("A lighthouse keeper"), WAIT);
      expect(api.scenarioCreates).toHaveLength(1);
    });

    it("clamps a pasted long idea to 150 characters instead of rejecting it", async () => {
      const api = installStudioApi();
      renderStudio({ path: "/studio/new" });
      const user = userEvent.setup();

      const idea = await screen.findByLabelText("One line idea");
      await user.click(idea);
      await user.paste("x".repeat(400));

      await waitFor(() => expect(api.scenarioCreates).toHaveLength(1), WAIT);
      expect((api.scenarioCreates[0].logline as string).length).toBe(150);
      expect(idea).toHaveValue("x".repeat(150));
    });
  });

  describe("tabs", () => {
    it("shows the Guide first and focuses an item that is already open", async () => {
      installStudioApi({ scenario: buildScenarioFixture(), entities: [mara, lighthouse] });
      renderStudio({ path: EDIT_PATH });
      const user = userEvent.setup();

      await screen.findByRole("tab", { name: "Guide" });
      await user.click(await screen.findByRole("button", { name: "Mara" }));
      await user.click(await screen.findByRole("button", { name: "The Lighthouse" }));
      await user.click(screen.getByRole("button", { name: "Mara" }));

      expect(screen.getAllByRole("tab", { name: "Mara" })).toHaveLength(1);
      expect(screen.getByRole("tab", { name: "Mara" })).toHaveAttribute("aria-selected", "true");
    });

    it("splits a tab to the right from its menu and closes tabs", async () => {
      installStudioApi({ scenario: buildScenarioFixture(), entities: [mara] });
      renderStudio({ path: EDIT_PATH });
      const user = userEvent.setup();

      await user.click(await screen.findByRole("button", { name: "Mara" }));
      await user.click(screen.getByRole("button", { name: "Tab options for Mara" }));
      await user.click(screen.getByRole("menuitem", { name: "Split right" }));

      expect(within(await screen.findByRole("region", { name: "Split tab" })).getByLabelText("Name")).toHaveValue("Mara");
      expect(screen.getByRole("region", { name: "Active tab" })).toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: "Close Mara" }));
      expect(screen.queryByRole("region", { name: "Split tab" })).toBeNull();
      expect(screen.queryByRole("tab", { name: "Mara" })).toBeNull();
    });

    it("restores the tabs remembered for this story", async () => {
      localStorage.setItem(
        `${STUDIO_TABS_STORAGE_PREFIX}${STUDIO_TEST_SCENARIO_ID}`,
        JSON.stringify({
          openTabIds: [GUIDE_TAB_ID, buildCardTabId("mara")],
          activeTabId: buildCardTabId("mara"),
          splitTabId: null,
          guideStep: 2,
        }),
      );
      installStudioApi({ scenario: buildScenarioFixture(), entities: [mara] });
      renderStudio({ path: EDIT_PATH });

      expect(await screen.findByRole("tab", { name: "Mara" })).toHaveAttribute("aria-selected", "true");
    });

    it("opens only the Guide when localStorage is unavailable", async () => {
      vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
        throw new Error("blocked");
      });
      vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
        throw new Error("blocked");
      });
      installStudioApi({ scenario: buildScenarioFixture(), entities: [mara] });
      renderStudio({ path: EDIT_PATH });

      expect(await screen.findByRole("tab", { name: "Guide" })).toBeInTheDocument();
      expect(screen.getAllByRole("tab")).toHaveLength(1);
      vi.restoreAllMocks();
    });

    it("drops a remembered card tab whose card no longer exists", async () => {
      localStorage.setItem(
        `${STUDIO_TABS_STORAGE_PREFIX}${STUDIO_TEST_SCENARIO_ID}`,
        JSON.stringify({
          openTabIds: [GUIDE_TAB_ID, buildCardTabId("ghost")],
          activeTabId: GUIDE_TAB_ID,
          splitTabId: null,
          guideStep: 1,
        }),
      );
      installStudioApi({ scenario: buildScenarioFixture(), entities: [mara] });
      renderStudio({ path: EDIT_PATH });

      await screen.findByRole("tab", { name: "Guide" });
      await waitFor(() => expect(screen.getAllByRole("tab")).toHaveLength(1), WAIT);
    });
  });

  describe("Your story", () => {
    it("shows card counts per group and filters by name", async () => {
      installStudioApi({ scenario: buildScenarioFixture(), entities: [mara, tomas, lighthouse] });
      renderStudio({ path: EDIT_PATH });
      const user = userEvent.setup();

      const characters = await screen.findByRole("region", { name: "Characters" });
      expect(await within(characters).findByText("2")).toBeInTheDocument();
      expect(within(screen.getByRole("region", { name: "Places" })).getByText("1")).toBeInTheDocument();
      expect(within(screen.getByRole("region", { name: "Groups" })).getByText("0")).toBeInTheDocument();

      await user.type(screen.getByRole("searchbox", { name: "Filter your story by name" }), "mar");
      expect(screen.getByRole("button", { name: "Mara" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Tomas" })).toBeNull();
      expect(screen.queryByRole("region", { name: "Places" })).toBeNull();
    });

    it("lists the Guide steps with a status a screen reader can read", async () => {
      installStudioApi({
        scenario: buildScenarioFixture({ title: "The Door", logline: "A door in the sea" }),
      });
      renderStudio({ path: EDIT_PATH });

      const guide = await screen.findByRole("region", { name: "Guide" });
      expect(within(guide).getByRole("button", { name: /Done\s*1\. Idea/ })).toBeInTheDocument();
      expect(within(guide).getByRole("button", { name: /2\. Premise/ })).toBeInTheDocument();
    });

    it("offers no Advanced switch and says why on a phone", async () => {
      installStudioApi({ scenario: buildScenarioFixture() });
      setMatchMedia(true);
      renderStudio({ path: EDIT_PATH });

      expect(
        (await screen.findAllByText("Advanced mode works on a larger screen."))[0],
      ).toBeInTheDocument();
    });

    it("shows an N open switcher instead of the tab strip on a phone", async () => {
      installStudioApi({ scenario: buildScenarioFixture(), entities: [mara] });
      setMatchMedia(true);
      renderStudio({ path: EDIT_PATH });
      const user = userEvent.setup();

      expect(await screen.findByRole("button", { name: "Open tabs" })).toHaveTextContent("1 open");
      expect(screen.queryByRole("tablist")).toBeNull();
      act(() => useStudioTabsStore.getState().openTab(buildCardTabId("mara")));
      expect(await screen.findByRole("button", { name: "Open tabs" })).toHaveTextContent("2 open");
      await user.click(screen.getByRole("button", { name: "Open tabs" }));
      expect(screen.getByRole("menuitem", { name: "Mara" })).toBeInTheDocument();
    });
  });

  describe("top bar", () => {
    it("says editing is locked while the story is publishing", async () => {
      installStudioApi({ scenario: buildScenarioFixture({ status: "publishing" }) });
      renderStudio({ path: EDIT_PATH });

      expect(
        (await screen.findAllByText("Publishing… editing unlocks when it's done."))[0],
      ).toBeInTheDocument();
    });

    it("shows the reload notice when the story changed in another window", async () => {
      installStudioApi({ scenario: buildScenarioFixture() });
      renderStudio({ path: EDIT_PATH });
      await screen.findByRole("tab", { name: "Guide" });

      act(() => useStudioStore.getState().setHasEditConflict(true));

      expect(
        await screen.findByText("This story changed in another window. Reload to see the latest."),
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Reload" })).toBeInTheDocument();
    });

    it("edits the story name inline and keeps it in step with the Idea step", async () => {
      const api = installStudioApi({ scenario: buildScenarioFixture() });
      renderStudio({ path: EDIT_PATH });
      const user = userEvent.setup();

      await user.type(await screen.findByLabelText("Story name"), "The Door");

      await waitFor(() => expect(api.scenarioUpdates.at(-1)).toMatchObject({ title: "The Door" }), WAIT);
      await waitFor(
        () => expect(screen.getByLabelText("What is the name of the story?")).toHaveValue("The Door"),
        WAIT,
      );
    });

    it("sends the cached content_edited_at with a save", async () => {
      const api = installStudioApi({ scenario: buildScenarioFixture() });
      renderStudio({ path: EDIT_PATH });
      const user = userEvent.setup();

      await user.type(await screen.findByLabelText("Story name"), "A");
      await waitFor(() => expect(api.scenarioUpdates).toHaveLength(1), WAIT);
      expect(api.scenarioUpdates[0].expected_content_edited_at).toBe(buildScenarioFixture().content_edited_at);
    });
  });

  it("shows the reload notice and keeps the typed text when the server says the story changed", async () => {
    installStudioApi({ scenario: buildScenarioFixture() });
    server.use(
      http.patch("*/v1/scenarios/:scenarioId", () =>
        HttpResponse.json(
          { detail: "This story changed in another window. Reload to see the latest.", code: "scenario_edit_conflict" },
          { status: 409 },
        ),
      ),
    );
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();

    await user.type(await screen.findByLabelText("Story name"), "Mine");

    expect(await screen.findByRole("alert", {}, WAIT)).toHaveTextContent(
      "This story changed in another window. Reload to see the latest.",
    );
    expect(screen.getByLabelText("Story name")).toHaveValue("Mine");
  });

  it("adds a character from the + menu and opens its tab", async () => {
    const api = installStudioApi({ scenario: buildScenarioFixture() });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "New tab" }));
    await user.click(screen.getByRole("menuitem", { name: "New character" }));

    await waitFor(() => expect(api.entities).toHaveLength(1), WAIT);
    expect(await screen.findByRole("tab", { name: "New character" })).toHaveAttribute("aria-selected", "true");
  });

  it("adds a place from the Your story group and opens its tab", async () => {
    const api = installStudioApi({ scenario: buildScenarioFixture() });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Add to Places" }));

    await waitFor(() => expect(api.entities).toHaveLength(1), WAIT);
    expect(api.entities[0]).toMatchObject({ entity_type: "location" });
    expect(await screen.findByRole("tab", { name: "New place" })).toBeInTheDocument();
  });

  it("keeps the master creation flow behind its own address", async () => {
    installStudioApi();
    renderStudio({ path: "/studio/new?mode=master" });
    expect(await screen.findByRole("heading", { name: "Master Mode" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Guide" })).toBeNull();
  });

  it("opens master stories in the Guide with Advanced mode on", async () => {
    installStudioApi({ scenario: buildScenarioFixture({ mode: "master", title: "Night Desk" }) });
    renderStudio({ path: EDIT_PATH });

    expect(await screen.findByRole("tab", { name: "Guide" })).toBeInTheDocument();
    expect(screen.queryByText("Master mode")).toBeNull();
  });

  it("keeps the master editor behind its own address for master stories", async () => {
    installStudioApi({ scenario: buildScenarioFixture({ mode: "master", title: "Night Desk" }) });
    renderStudio({ path: `${EDIT_PATH}?editor=full` });

    expect(await screen.findByText("Master mode")).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Guide" })).toBeNull();
  });

  it("sends a Guide step saved under Advanced mode back to Opening once the story is plain", async () => {
    localStorage.setItem(
      `${STUDIO_TABS_STORAGE_PREFIX}${STUDIO_TEST_SCENARIO_ID}`,
      JSON.stringify({
        openTabIds: [GUIDE_TAB_ID],
        activeTabId: GUIDE_TAB_ID,
        splitTabId: null,
        guideStep: 7,
        isGuideStepAdvanced: true,
      }),
    );
    installStudioApi({ scenario: buildScenarioFixture({ mode: "newbie", title: "Night Desk" }) });
    renderStudio({ path: EDIT_PATH });

    await waitFor(() => expect(useStudioTabsStore.getState().guideStep).toBe(6), WAIT);
    expect(useStudioTabsStore.getState().isGuideStepAdvanced).toBe(false);
  });

  it("keeps a plain Finish step on Finish when the story went Advanced elsewhere", async () => {
    localStorage.setItem(
      `${STUDIO_TABS_STORAGE_PREFIX}${STUDIO_TEST_SCENARIO_ID}`,
      JSON.stringify({
        openTabIds: [GUIDE_TAB_ID],
        activeTabId: GUIDE_TAB_ID,
        splitTabId: null,
        guideStep: 7,
        isGuideStepAdvanced: false,
      }),
    );
    installStudioApi({ scenario: buildScenarioFixture({ mode: "master", title: "Night Desk" }) });
    renderStudio({ path: EDIT_PATH });

    await waitFor(() => expect(useStudioTabsStore.getState().guideStep).toBe(12), WAIT);
  });

  it("offers a way back to the Guide from the master editor", async () => {
    installStudioApi({ scenario: buildScenarioFixture({ mode: "master", title: "Night Desk" }) });
    renderStudio({ path: `${EDIT_PATH}?editor=full` });
    const user = userEvent.setup();

    await user.click(await screen.findByRole("link", { name: "Back to Guide" }));

    expect(await screen.findByRole("tab", { name: "Guide" })).toBeInTheDocument();
    expect(screen.queryByText("Master mode")).toBeNull();
  });

  it("keeps the idea text field mounted when the draft is created (no lost focus)", async () => {
    installStudioApi();
    renderStudio({ path: "/studio/new" });
    const user = userEvent.setup();

    const idea = await screen.findByLabelText("One line idea");
    await user.type(idea, "ab");
    await waitFor(() => expect(screen.getByLabelText("Story name")).toBeInTheDocument());
    await user.type(idea, "cd");

    expect(screen.getByLabelText("One line idea")).toBe(idea);
    expect(idea).toHaveValue("abcd");
  });
});
