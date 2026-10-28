import { screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { renderGuideStep } from "../../test/renderGuideStep";
import {
  buildConditionFixture,
  buildMinigameFixture,
  buildScenarioFixture,
  buildSheetRuleFixture,
} from "../../test/studioApiMock";
import { StudioTabPanel } from "../StudioFrame/StudioTabPanel";
import { StepExtras } from "./StepExtras";

const WAIT = { timeout: 4000 };

const openStep = (
  mode: "master" | "newbie" = "master",
  init: Parameters<typeof renderGuideStep>[1] = {},
) =>
  renderGuideStep(<StepExtras />, {
    scenario: buildScenarioFixture({ mode }),
    ...init,
  });

const extraCard = async (name: string) => within(await screen.findByRole("article", { name: `Extra ${name}` }));

describe("StepExtras", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
  });

  it("lists the extras in the spec order with a one-line description", async () => {
    await openStep();
    const cards = await screen.findAllByRole("article");
    expect(cards.map((card) => within(card).getByRole("heading").textContent)).toEqual([
      "Map",
      "Mood music",
      "Minigames",
      "Atmosphere",
      "Rule sheet",
      "Rule checks",
    ]);
    expect(screen.getByText("Let players see where they are. Uses your Places.")).toBeInTheDocument();
    expect(screen.getByText("Timed prompts and memory tests for the player.")).toBeInTheDocument();
  });

  it("enables the tool first, then opens the editor tab", async () => {
    const { api, user } = await openStep();
    const card = await extraCard("Rule checks");

    await user.click(card.getByRole("button", { name: "Add" }));

    await waitFor(() => expect(api.toolPuts).toEqual([["rule_checks"]]), WAIT);
    await waitFor(() => expect(useStudioTabsStore.getState().activeTabId).toBe("feature:extra-rule_checks"), WAIT);
    expect(within(await screen.findByRole("article", { name: "Extra Rule checks" })).getByText("On")).toBeInTheDocument();
  });

  it("brings the status display along when Atmosphere is added", async () => {
    const { api, user } = await openStep();
    await user.click((await extraCard("Atmosphere")).getByRole("button", { name: "Add" }));

    await waitFor(() => expect(api.scenario?.enabled_tools).toEqual(["status_hud", "atmosphere"]), WAIT);
  });

  it("opens the minigame editor without enabling the rhythm tool", async () => {
    const { api, user } = await openStep();
    await user.click((await extraCard("Minigames")).getByRole("button", { name: "Add" }));

    await waitFor(() => expect(useStudioTabsStore.getState().activeTabId).toBe("feature:extra-minigames"), WAIT);
    expect(api.toolPuts).toEqual([]);
  });

  it("shows Minigames as On when the story already has minigames of any type", async () => {
    await openStep("master", {
      scenario: buildScenarioFixture({ mode: "master", enabled_tools: [] }),
      minigames: [buildMinigameFixture({ minigame_id: "g1", minigame_type: "dodge" })],
    });
    const card = await extraCard("Minigames");

    await waitFor(() => expect(card.getByText("On")).toBeInTheDocument(), WAIT);
    expect(card.getByRole("button", { name: "Edit" })).toBeInTheDocument();
  });

  it("opens the map editor without a tool", async () => {
    const { api, user } = await openStep();
    await user.click((await extraCard("Map")).getByRole("button", { name: "Add" }));

    await waitFor(() => expect(useStudioTabsStore.getState().activeTabId).toBe("feature:extra-map"), WAIT);
    expect(api.toolPuts).toEqual([]);
  });

  it("shows On, Edit and Remove for an enabled extra, and Remove turns its tool off after asking", async () => {
    const { api, user } = await openStep("master", {
      scenario: buildScenarioFixture({ mode: "master", enabled_tools: ["rule_sheet"] }),
      sheetRules: [buildSheetRuleFixture({ rule_id: "r1" })],
    });
    const card = await extraCard("Rule sheet");
    expect(card.getByText("On")).toBeInTheDocument();
    expect(card.getByRole("button", { name: "Edit" })).toBeInTheDocument();

    await user.click(await waitFor(() => {
      const button = card.getByRole("button", { name: "Remove" });
      expect(button).toBeEnabled();
      return button;
    }, WAIT));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Turn off Rules & clipboard too?")).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Turn off" }));

    await waitFor(() => expect(api.toolPuts.at(-1)).toEqual([]), WAIT);
  });

  it("keeps a tool on when something else in the story still uses it", async () => {
    const { api, user } = await openStep("master", {
      scenario: buildScenarioFixture({ mode: "master", enabled_tools: ["status_hud", "atmosphere"] }),
      conditions: [buildConditionFixture({ condition_id: "c1", sensory_cue: "wind" })],
    });
    const card = await extraCard("Atmosphere");
    await user.click(await waitFor(() => {
      const button = card.getByRole("button", { name: "Remove" });
      expect(button).toBeEnabled();
      return button;
    }, WAIT));
    const dialog = await screen.findByRole("dialog");

    expect(within(dialog).getByText(/still uses it, so it stays on/)).toBeInTheDocument();
    expect(within(dialog).queryByRole("button", { name: "Turn off" })).toBeNull();
    await user.click(within(dialog).getByRole("button", { name: "OK" }));
    expect(api.toolPuts).toEqual([]);
  });

  it("closes the extra's editor tab when its tool is turned off", async () => {
    const { user } = await openStep("master", {
      scenario: buildScenarioFixture({ mode: "master", enabled_tools: ["rule_checks"] }),
    });
    useStudioTabsStore.getState().openTab("feature:extra-rule_checks");
    useStudioTabsStore.getState().focusTab("guide");
    const card = await extraCard("Rule checks");
    await user.click(await waitFor(() => {
      const button = card.getByRole("button", { name: "Remove" });
      expect(button).toBeEnabled();
      return button;
    }, WAIT));
    await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Turn off" }));

    await waitFor(() => expect(useStudioTabsStore.getState().openTabIds).not.toContain("feature:extra-rule_checks"), WAIT);
  });

  it("shows no extra as On when the story is not in Advanced mode, even if tools are stored", async () => {
    await openStep("newbie", {
      scenario: buildScenarioFixture({ mode: "newbie", enabled_tools: ["rule_checks", "status_hud"] }),
    });
    const card = await extraCard("Rule checks");
    expect(card.queryByText("On")).toBeNull();
    expect(card.getByRole("button", { name: "Add" })).toBeInTheDocument();
  });
});

describe("Extra editor tabs", () => {
  it("enables the rhythm tool only when a rhythm minigame is saved", async () => {
    const { api, user } = await renderGuideStep(<StudioTabPanel tabId="feature:extra-minigames" />, {
      scenario: buildScenarioFixture({
        mode: "master",
        enabled_tools: [],
        state_schema: { sanity: { type: "number", label: "Sanity" } },
      }),
    });

    await user.click(await screen.findByRole("button", { name: /new minigame/i }));
    await user.type(screen.getByLabelText(/^label$/i), "The Hum");
    await user.selectOptions(screen.getByLabelText("Minigame type"), "rhythm_composure");
    const paths = screen.getAllByLabelText(/mutation 1 path/i);
    await user.type(paths[0], "sanity");
    await user.type(paths[1], "sanity");
    expect(api.toolPuts).toEqual([]);
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => expect(api.toolPuts).toEqual([["composure"]]), WAIT);
    await waitFor(() => expect(api.minigames.map((game) => game.minigame_type)).toEqual(["rhythm_composure"]), WAIT);
  });

  it("does not enable the rhythm tool for another minigame type", async () => {
    const { api, user } = await renderGuideStep(<StudioTabPanel tabId="feature:extra-minigames" />, {
      scenario: buildScenarioFixture({
        mode: "master",
        enabled_tools: [],
        state_schema: { sanity: { type: "number", label: "Sanity" } },
      }),
    });

    await user.click(await screen.findByRole("button", { name: /new minigame/i }));
    await user.type(screen.getByLabelText(/^label$/i), "Dodge");
    const paths = screen.getAllByLabelText(/mutation 1 path/i);
    await user.type(paths[0], "sanity");
    await user.type(paths[1], "sanity");
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => expect(api.minigames).toHaveLength(1), WAIT);
    expect(api.toolPuts).toEqual([]);
  });

  it("tells the creator to turn Advanced mode on instead of opening a stale extra tab", async () => {
    await renderGuideStep(<StudioTabPanel tabId="feature:extra-rule_checks" />, {
      scenario: buildScenarioFixture({ mode: "newbie", enabled_tools: [] }),
    });

    expect(await screen.findByText("Turn Advanced mode on to use Rule checks.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Rule checks" })).toBeNull();
  });

  it("opens the existing editor for an extra with a way back to Extras", async () => {
    const { user } = await renderGuideStep(<StudioTabPanel tabId="feature:extra-rule_checks" />, {
      scenario: buildScenarioFixture({ mode: "master", enabled_tools: ["rule_checks"] }),
    });

    expect(await screen.findByRole("heading", { name: "Rule checks" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "← Back to Extras" }));
    expect(useStudioTabsStore.getState().activeTabId).toBe("guide");
    expect(useStudioTabsStore.getState().guideStep).toBe(11);
  });
});
