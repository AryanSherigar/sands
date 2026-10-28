import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useToastStore } from "@/shared/stores/toast.store";
import { server } from "@/test/msw/server";
import { useStudioStore } from "../../stores/studio.store";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { renderStudio } from "../../test/renderStudio";
import {
  STUDIO_TEST_SCENARIO_ID,
  buildConditionFixture,
  buildEndConditionFixture,
  buildInvariantFixture,
  buildScenarioFixture,
  installStudioApi,
} from "../../test/studioApiMock";

const EDIT_PATH = `/studio/${STUDIO_TEST_SCENARIO_ID}/edit`;
const WAIT = { timeout: 4000 };
const OPENING_STEP = 6;
const LARGER_SCREEN_COPY = "Advanced mode works on a larger screen.";
const PUBLISHING_COPY = "Publishing… editing unlocks when it's done.";
const TURN_OFF_COPY =
  'Your endings, values and rules are kept but switched off. Links with an "only when" condition stop applying until you turn Advanced mode back on. Turn it back on anytime to use everything again.';

const setNarrowScreen = (): void => {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: query.includes("max-width: 1023px"),
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })) as unknown as typeof window.matchMedia;
};

const openStudio = async (
  init: Parameters<typeof installStudioApi>[0] = {},
  stepNumber = OPENING_STEP,
) => {
  const api = installStudioApi({ scenario: buildScenarioFixture(), ...init });
  const view = renderStudio({ path: EDIT_PATH });
  await screen.findByRole("tab", { name: "Guide" });
  act(() => useStudioTabsStore.getState().setGuideStep(stepNumber));
  return { api, ...view };
};

const getStepBar = async (): Promise<HTMLElement> =>
  screen.findByRole("navigation", { name: "Guide steps" });

const getTopBar = (): HTMLElement => {
  const bar = screen.getByLabelText("Story name").closest("header");
  if (!bar) throw new Error("Top bar not found");
  return bar;
};

const getSwitchRow = (): HTMLElement => screen.getByRole("group", { name: "Advanced mode switch" });

const goToInvitation = async (): Promise<ReturnType<typeof userEvent.setup>> => {
  const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: "Next" }));
  await screen.findByRole("region", { name: "Advanced mode" });
  return user;
};

describe("Advanced mode switch", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
    useStudioStore.getState().setHasEditConflict(false);
    useToastStore.setState({ queue: [] });
    // @ts-expect-error jsdom has no matchMedia unless a test installs one
    delete window.matchMedia;
  });

  describe("invitation", () => {
    it("turns Advanced on, saves mode master and continues to Endings in a 12 step Guide", async () => {
      const { api } = await openStudio();
      const user = await goToInvitation();
      const turnOn = within(screen.getByRole("region", { name: "Advanced mode" })).getByRole(
        "button",
        { name: "Turn on Advanced mode" },
      );
      expect(turnOn).toBeEnabled();

      await user.click(turnOn);

      await waitFor(() => expect(api.scenarioUpdates.some((body) => body.mode === "master")).toBe(true), WAIT);
      expect(await screen.findByRole("heading", { name: "How can the story end?" })).toBeInTheDocument();
      expect(within(await getStepBar()).getByText("Step 7 of 12")).toBeInTheDocument();
    });

    it("goes to Finish on Not now and keeps the seven step Guide", async () => {
      const { api } = await openStudio();
      const user = await goToInvitation();

      await user.click(screen.getByRole("button", { name: "Not now" }));

      expect(await screen.findByRole("heading", { name: "Ready to share your story?" })).toBeInTheDocument();
      expect(within(await getStepBar()).getByText("Step 7 of 7")).toBeInTheDocument();
      expect(api.scenarioUpdates.some((body) => "mode" in body)).toBe(false);
    });

    it("stays on the invitation and tells the creator when the switch fails", async () => {
      const { api } = await openStudio();
      server.use(
        http.patch("*/v1/scenarios/:scenarioId", () =>
          HttpResponse.json({ detail: "nope" }, { status: 500 }),
        ),
      );
      const user = await goToInvitation();

      await user.click(screen.getByRole("button", { name: "Turn on Advanced mode" }));

      await waitFor(
        () =>
          expect(useToastStore.getState().queue.map((item) => item.message)).toContain(
            "Couldn't switch Advanced mode. Try again.",
          ),
        WAIT,
      );
      expect(screen.getByRole("region", { name: "Advanced mode" })).toBeInTheDocument();
      expect(api.scenario?.mode).toBe("newbie");
    });
  });

  describe("Your story row", () => {
    it("toggles On and Off with a confirmation, keeping data and returning to seven steps", async () => {
      const { api } = await openStudio({}, 1);
      const user = userEvent.setup();
      const row = getSwitchRow();
      expect(within(row).getByText("Advanced mode · Off")).toBeInTheDocument();
      expect(screen.queryByRole("region", { name: "Advanced" })).toBeNull();

      await user.click(within(row).getByRole("button", { name: "Turn on" }));

      expect(await within(row).findByText("Advanced mode · On")).toBeInTheDocument();
      expect(within(await getStepBar()).getByText("Step 1 of 12")).toBeInTheDocument();
      const rail = await screen.findByRole("region", { name: "Advanced" });
      expect(within(rail).getByRole("button", { name: /Endings/ })).toBeInTheDocument();
      expect(within(rail).getByRole("button", { name: /Tracked values/ })).toBeInTheDocument();
      expect(within(rail).getByRole("button", { name: /Rules/ })).toBeInTheDocument();
      expect(within(rail).getByRole("button", { name: /Hard limits/ })).toBeInTheDocument();
      expect(within(rail).getByRole("button", { name: /Extras/ })).toBeInTheDocument();

      await user.click(within(row).getByRole("button", { name: "Turn off" }));
      const dialog = await screen.findByRole("dialog");
      expect(within(dialog).getByText(TURN_OFF_COPY)).toBeInTheDocument();
      await user.click(within(dialog).getByRole("button", { name: "Turn off Advanced mode" }));

      expect(await within(row).findByText("Advanced mode · Off")).toBeInTheDocument();
      expect(api.scenarioUpdates.filter((body) => "mode" in body).map((body) => body.mode)).toEqual([
        "master",
        "newbie",
      ]);
      expect(within(await getStepBar()).getByText("Step 1 of 7")).toBeInTheDocument();
      expect(screen.queryByRole("region", { name: "Advanced" })).toBeNull();
    });

    it("leaves Advanced on when the creator cancels the confirmation", async () => {
      const { api } = await openStudio({ scenario: buildScenarioFixture({ mode: "master" }) }, 1);
      const user = userEvent.setup();
      await user.click(within(getSwitchRow()).getByRole("button", { name: "Turn off" }));
      const dialog = await screen.findByRole("dialog");

      await user.click(within(dialog).getByRole("button", { name: "Cancel" }));

      expect(screen.queryByRole("dialog")).toBeNull();
      expect(within(getSwitchRow()).getByText("Advanced mode · On")).toBeInTheDocument();
      expect(api.scenarioUpdates.some((body) => "mode" in body)).toBe(false);
    });

    it("warns in the confirmation when the story lacks an idea or an opening", async () => {
      await openStudio({ scenario: buildScenarioFixture({ mode: "master", title: "Lantern", logline: null }) }, 1);
      const user = userEvent.setup();
      await user.click(within(getSwitchRow()).getByRole("button", { name: "Turn off" }));
      const dialog = await screen.findByRole("dialog");

      expect(
        within(dialog).getByText(
          "Without Advanced mode, publishing needs: one line idea, opening. Add them before you publish changes.",
        ),
      ).toBeInTheDocument();
    });

    it("shows no publishing warning when the story has its idea and opening", async () => {
      await openStudio(
        {
          scenario: buildScenarioFixture({
            mode: "master",
            title: "Lantern",
            logline: "A keeper guards a failing light.",
            opening_scene: "The storm rolls in.",
          }),
        },
        1,
      );
      const user = userEvent.setup();
      await user.click(within(getSwitchRow()).getByRole("button", { name: "Turn off" }));
      const dialog = await screen.findByRole("dialog");

      expect(within(dialog).getByText(TURN_OFF_COPY)).toBeInTheDocument();
      expect(within(dialog).queryByRole("note")).toBeNull();
    });

    it("moves Finish with the mode and falls back to Opening from an Advanced step", async () => {
      await openStudio({ scenario: buildScenarioFixture({ mode: "master" }) }, 9);
      const user = userEvent.setup();
      expect(within(await getStepBar()).getByText("Step 9 of 12")).toBeInTheDocument();

      await user.click(within(getSwitchRow()).getByRole("button", { name: "Turn off" }));
      await user.click(
        within(await screen.findByRole("dialog")).getByRole("button", { name: "Turn off Advanced mode" }),
      );

      expect(await screen.findByRole("heading", { name: "Where does the story begin?" })).toBeInTheDocument();
      expect(within(await getStepBar()).getByText("Step 6 of 7")).toBeInTheDocument();
    });

    it("counts endings, rules and hard limits next to their rail entries", async () => {
      await openStudio(
        {
          scenario: buildScenarioFixture({
            mode: "master",
            state_schema: {
              oil: { type: "number", label: "Lantern oil" },
              note: { type: "string", label: "Note" },
            },
          }),
          endConditions: [
            buildEndConditionFixture({ end_condition_id: "e1" }),
            buildEndConditionFixture({ end_condition_id: "e2" }),
          ],
          conditions: [buildConditionFixture({ condition_id: "c1" })],
          invariants: [buildInvariantFixture({ invariant_id: "i1" })],
        },
        1,
      );
      const rail = await screen.findByRole("region", { name: "Advanced" });

      await waitFor(() => expect(within(rail).getByRole("button", { name: /Endings/ })).toHaveTextContent("2"), WAIT);
      expect(within(rail).getByRole("button", { name: /Tracked values/ })).toHaveTextContent("1");
      expect(within(rail).getByRole("button", { name: /Rules/ })).toHaveTextContent("1");
      expect(within(rail).getByRole("button", { name: /Hard limits/ })).toHaveTextContent("1");
    });

    it("opens the matching Guide step from a rail entry", async () => {
      await openStudio({ scenario: buildScenarioFixture({ mode: "master" }) }, 1);
      const user = userEvent.setup();
      const rail = await screen.findByRole("region", { name: "Advanced" });

      await user.click(within(rail).getByRole("button", { name: /Hard limits/ }));

      expect(await screen.findByRole("heading", { name: "What can never happen?" })).toBeInTheDocument();
      expect(within(await getStepBar()).getByText("Step 10 of 12")).toBeInTheDocument();
    });
  });

  describe("Your story rail", () => {
    it("lists only the base steps under Guide and the Advanced steps once under Advanced", async () => {
      await openStudio({ scenario: buildScenarioFixture({ mode: "master" }) }, 1);
      const guide = await screen.findByRole("region", { name: "Guide" });
      const advanced = await screen.findByRole("region", { name: "Advanced" });

      expect(within(guide).getAllByRole("button").slice(1).map((button) => button.textContent)).toEqual([
        expect.stringContaining("1. Idea"),
        expect.stringContaining("2. Premise"),
        expect.stringContaining("3. Player"),
        expect.stringContaining("4. Characters"),
        expect.stringContaining("5. World"),
        expect.stringContaining("6. Opening"),
        expect.stringContaining("12. Finish"),
      ]);
      expect(within(guide).queryByRole("button", { name: /Endings/ })).toBeNull();
      expect(within(advanced).getAllByRole("button").slice(1)).toHaveLength(5);
    });

    it("opens the Opening step when a remembered Advanced step no longer exists", async () => {
      await openStudio({}, 9);
      expect(await screen.findByRole("heading", { name: "Where does the story begin?" })).toBeInTheDocument();
      expect(within(await getStepBar()).getByText("Step 6 of 7")).toBeInTheDocument();
    });
  });

  describe("Your story menu", () => {
    it("offers the full editor for Advanced stories and opens it", async () => {
      await openStudio({ scenario: buildScenarioFixture({ mode: "master", title: "Night Desk" }) }, 1);
      const user = userEvent.setup();

      await user.click(await screen.findByRole("button", { name: "Story options" }));
      await user.click(screen.getByRole("menuitem", { name: "Open full editor" }));

      expect(await screen.findByText("Master mode")).toBeInTheDocument();
    });

    it("does not offer the full editor when Advanced mode is off", async () => {
      await openStudio({}, 1);
      await userEvent.setup().click(await screen.findByRole("button", { name: "Story options" }));

      expect(screen.queryByRole("menuitem", { name: "Open full editor" })).toBeNull();
      expect(screen.queryByRole("menuitem", { name: "View stats" })).toBeNull();
    });

    it("offers stats for a published story", async () => {
      await openStudio({ scenario: buildScenarioFixture({ status: "published" }) }, 1);
      await userEvent.setup().click(await screen.findByRole("button", { name: "Story options" }));

      expect(screen.getByRole("menuitem", { name: "View stats" })).toBeInTheDocument();
    });
  });

  describe("badge and legacy stories", () => {
    it("shows the Advanced mode badge in the top bar only when on", async () => {
      const user = userEvent.setup();
      await openStudio({}, 1);
      const topBar = within(getTopBar());
      expect(topBar.queryByText("Advanced mode")).toBeNull();

      await user.click(within(getSwitchRow()).getByRole("button", { name: "Turn on" }));

      expect(await topBar.findByText("Advanced mode")).toBeInTheDocument();
    });

    it("opens a legacy master story with Advanced on and twelve steps", async () => {
      await openStudio({ scenario: buildScenarioFixture({ mode: "master" }) }, 1);
      expect(within(await getStepBar()).getByText("Step 1 of 12")).toBeInTheDocument();
      expect(within(getTopBar()).getByText("Advanced mode")).toBeInTheDocument();
      expect(within(getSwitchRow()).getByText("Advanced mode · On")).toBeInTheDocument();
    });
  });

  describe("small screens and publishing", () => {
    it("offers no switch below 1024px", async () => {
      setNarrowScreen();
      await openStudio();
      expect(within(getSwitchRow()).getByText(LARGER_SCREEN_COPY)).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Turn on" })).toBeNull();

      const user = userEvent.setup();
      await user.click(await screen.findByRole("button", { name: "Next" }));
      const invitation = await screen.findByRole("region", { name: "Advanced mode" });
      expect(within(invitation).getByText(LARGER_SCREEN_COPY)).toBeInTheDocument();
      expect(within(invitation).queryByRole("button", { name: "Turn on Advanced mode" })).toBeNull();
    });

    it("disables the switch while publishing", async () => {
      await openStudio({ scenario: buildScenarioFixture({ status: "publishing" }) }, 1);
      const row = getSwitchRow();
      expect(within(row).getByText(PUBLISHING_COPY)).toBeInTheDocument();
      expect(within(row).getByRole("button", { name: "Turn on" })).toBeDisabled();
    });
  });
});
