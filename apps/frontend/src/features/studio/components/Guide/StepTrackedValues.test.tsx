import { screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { renderGuideStep } from "../../test/renderGuideStep";
import {
  buildConditionFixture,
  buildEndConditionFixture,
  buildScenarioFixture,
} from "../../test/studioApiMock";
import { StepTrackedValues } from "./StepTrackedValues";

const WAIT = { timeout: 4000 };

const LANTERN_OIL = {
  type: "number" as const,
  label: "Lantern oil",
  min: 0,
  max: 10,
  initial: 10,
  description: "How much light is left",
};

const openStep = (
  init: Parameters<typeof renderGuideStep>[1] = {},
  schema: Record<string, unknown> = {},
) =>
  renderGuideStep(<StepTrackedValues />, {
    scenario: buildScenarioFixture({
      mode: "master",
      state_schema: schema as never,
    }),
    ...init,
  });

const savedSchema = (api: Awaited<ReturnType<typeof openStep>>["api"]): Record<string, Record<string, unknown>> =>
  (api.scenario?.state_schema ?? {}) as unknown as Record<string, Record<string, unknown>>;

describe("StepTrackedValues", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
  });

  describe("quick add", () => {
    it("adds Health as a bar and switches the status display on first", async () => {
      const { api, user } = await openStep();
      await user.click(screen.getByRole("button", { name: "Health" }));
      await waitFor(() => expect(savedSchema(api).health).toBeDefined(), WAIT);
      expect(savedSchema(api).health).toMatchObject({
        type: "number",
        label: "Health",
        min: 0,
        max: 10,
        initial: 10,
        display: { kind: "meter", label: "Health", clamp_min: 0, clamp_max: 10 },
      });
      expect(api.writeLog.indexOf("tools")).toBeLessThan(
        api.writeLog.findIndex((entry) => entry.startsWith("scenario:state_schema")),
      );
      expect(await screen.findByRole("region", { name: "What the player sees" })).toBeInTheDocument();
    });

    it("adds Trust, Money, Time and Sanity with their defaults", async () => {
      const { api, user } = await openStep();
      for (const name of ["Trust", "Money", "Time", "Sanity"]) {
        await user.click(screen.getByRole("button", { name }));
      }
      await waitFor(() => expect(Object.keys(savedSchema(api))).toEqual(["trust", "money", "time", "sanity"]), WAIT);
      const schema = savedSchema(api);
      expect(schema.trust).toMatchObject({ type: "number", min: 0, max: 10, initial: 5 });
      expect(schema.trust.display).toBeUndefined();
      expect(schema.money).toMatchObject({ type: "number", min: 0, initial: 0 });
      expect(schema.money.max).toBeUndefined();
      expect(schema.time).toMatchObject({ type: "enum", options: ["Dawn", "Day", "Dusk", "Night"], initial: "Dawn" });
      expect(schema.sanity.display).toMatchObject({
        kind: "meter",
        tiers: [{ name: "Steady", min: 7 }, { name: "Shaken", min: 4 }, { name: "Breaking" }],
      });
    });

    it("adds Your own value as a number to rename", async () => {
      const { api, user } = await openStep();
      await user.click(screen.getByRole("button", { name: "Your own…" }));
      await waitFor(() => expect(savedSchema(api).new_value).toBeDefined(), WAIT);
      expect(savedSchema(api).new_value).toMatchObject({ type: "number", label: "New value" });
    });

    it("marks a quick add that already exists and does not add it twice", async () => {
      const { user } = await openStep({}, { trust: { type: "number", label: "Trust", min: 0, max: 10, initial: 5 } });
      await screen.findByRole("article", { name: "Tracked value Trust" });
      const chip = screen.getByRole("button", { name: "Trust" });
      expect(chip).toHaveAttribute("aria-pressed", "true");
      await user.click(chip);
      expect(screen.getAllByRole("article")).toHaveLength(1);
    });
  });

  describe("value card", () => {
    it("offers only Number, Yes / no and Choice as types", async () => {
      await openStep({}, { lantern_oil: LANTERN_OIL });
      const card = await screen.findByRole("article", { name: "Tracked value Lantern oil" });
      const options = within(within(card).getByLabelText("Type")).getAllByRole("option");
      expect(options.map((option) => option.textContent)).toEqual(["Number", "Yes / no", "Choice"]);
    });

    it("edits starts at, lowest and highest and saves them", async () => {
      const { api, user } = await openStep({}, { lantern_oil: LANTERN_OIL });
      const card = await screen.findByRole("article", { name: "Tracked value Lantern oil" });
      const highest = within(card).getByLabelText("Highest");
      await user.clear(highest);
      await user.type(highest, "20");
      await waitFor(() => expect(savedSchema(api).lantern_oil.max).toBe(20), WAIT);
    });

    it("saves What it means as the field description", async () => {
      const { api, user } = await openStep({}, { lantern_oil: { ...LANTERN_OIL, description: undefined } });
      const card = await screen.findByRole("article", { name: "Tracked value Lantern oil" });
      await user.type(within(card).getByLabelText("What it means"), "Light left in the lantern");
      await waitFor(() => expect(savedSchema(api).lantern_oil.description).toBe("Light left in the lantern"), WAIT);
    });

    it("tags a value Needs details until What it means is filled", async () => {
      const { user } = await openStep({}, { lantern_oil: { ...LANTERN_OIL, description: undefined } });
      const card = await screen.findByRole("article", { name: "Tracked value Lantern oil" });
      expect(within(card).getByText("Needs details")).toBeInTheDocument();
      await user.type(within(card).getByLabelText("What it means"), "Light");
      expect(within(card).queryByText("Needs details")).toBeNull();
    });

    it("switches the display to Bar with the value's lowest and highest", async () => {
      const { api, user } = await openStep({}, { lantern_oil: LANTERN_OIL });
      const card = await screen.findByRole("article", { name: "Tracked value Lantern oil" });
      await user.selectOptions(within(card).getByLabelText("Player sees"), "Bar");
      await waitFor(() => expect(savedSchema(api).lantern_oil.display).toBeDefined(), WAIT);
      expect(savedSchema(api).lantern_oil.display).toMatchObject({
        kind: "meter",
        label: "Lantern oil",
        clamp_min: 0,
        clamp_max: 10,
      });
      expect(api.toolPuts).toEqual([["status_hud"]]);
    });

    it("hides a value from the player with the hidden flag and no display", async () => {
      const { api, user } = await openStep({}, { lantern_oil: LANTERN_OIL });
      const card = await screen.findByRole("article", { name: "Tracked value Lantern oil" });
      await user.selectOptions(within(card).getByLabelText("Player sees"), "Hidden");
      await waitFor(() => expect(savedSchema(api).lantern_oil.hidden).toBe(true), WAIT);
      expect(savedSchema(api).lantern_oil.display).toBeUndefined();
    });

    it("edits the levels of a bar by name and threshold", async () => {
      const levelled = {
        ...LANTERN_OIL,
        display: { kind: "meter", label: "Lantern oil", clamp_min: 0, clamp_max: 10, tiers: [{ name: "Bright", min: 5 }, { name: "Dim" }] },
      };
      const { api, user } = await openStep({}, { lantern_oil: levelled }, );
      const card = await screen.findByRole("article", { name: "Tracked value Lantern oil" });
      const name = within(card).getByLabelText("Level 1 name");
      await user.clear(name);
      await user.type(name, "Glowing");
      await waitFor(() => {
        const tiers = (savedSchema(api).lantern_oil.display as { tiers: Array<{ name: string }> }).tiers;
        expect(tiers[0].name).toBe("Glowing");
      }, WAIT);
    });

    it("keeps text values untouched and points to the full editor", async () => {
      await openStep({}, { diary: { type: "string", label: "Diary", initial: "" } });
      expect(await screen.findByText("Diary")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Edit in full editor" })).toBeInTheDocument();
      expect(screen.queryByRole("article", { name: "Tracked value Diary" })).toBeNull();
    });

    it("lists where a value is used and jumps to that step", async () => {
      const { user } = await openStep(
        {
          endConditions: [
            buildEndConditionFixture({
              end_condition_id: "ending-1",
              outcome_title: "Lights out",
              condition_expression: { field: "lantern_oil", op: "<=", value: 0 },
            }),
          ],
          conditions: [
            buildConditionFixture({
              condition_id: "rule-1",
              label: "Dim warning",
              condition_expression: { field: "lantern_oil", op: "<=", value: 2 },
            }),
          ],
        },
        { lantern_oil: LANTERN_OIL },
      );
      const card = await screen.findByRole("article", { name: "Tracked value Lantern oil" });
      const used = within(card).getByRole("group", { name: "Used in" });
      await user.click(await within(used).findByRole("button", { name: "Ending: Lights out" }));
      expect(useStudioTabsStore.getState().guideStep).toBe(7);
      expect(within(used).getByRole("button", { name: "Rule: Dim warning" })).toBeInTheDocument();
    });

    it("warns with the count before deleting a value that is in use", async () => {
      const { api, user } = await openStep(
        {
          endConditions: [
            buildEndConditionFixture({
              end_condition_id: "ending-1",
              condition_expression: { field: "lantern_oil", op: "<=", value: 0 },
            }),
          ],
          conditions: [
            buildConditionFixture({
              condition_id: "rule-1",
              condition_expression: { field: "lantern_oil", op: "<=", value: 2 },
            }),
          ],
        },
        { lantern_oil: LANTERN_OIL },
      );
      const card = await screen.findByRole("article", { name: "Tracked value Lantern oil" });
      await within(card).findByRole("button", { name: "Ending: Ending" });
      await user.click(within(card).getByRole("button", { name: "Lantern oil options" }));
      await user.click(screen.getByRole("menuitem", { name: "Delete" }));
      expect(await screen.findByText("Lantern oil is used in 2 places. Delete anyway?")).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Delete" }));
      await waitFor(() => expect(savedSchema(api).lantern_oil).toBeUndefined(), WAIT);
    });

    it("deletes an unused value without a warning", async () => {
      const { api, user } = await openStep({}, { lantern_oil: LANTERN_OIL });
      const card = await screen.findByRole("article", { name: "Tracked value Lantern oil" });
      await user.click(within(card).getByRole("button", { name: "Lantern oil options" }));
      await user.click(screen.getByRole("menuitem", { name: "Delete" }));
      await waitFor(() => expect(savedSchema(api).lantern_oil).toBeUndefined(), WAIT);
    });
  });

  describe("preview strip", () => {
    it("shows the player's status display for the values that have one", async () => {
      await openStep(
        {},
        {
          health: {
            type: "number",
            label: "Health",
            min: 0,
            max: 10,
            initial: 7,
            description: "x",
            display: { kind: "meter", label: "Health", clamp_min: 0, clamp_max: 10 },
          },
        },
      );
      const strip = await screen.findByRole("region", { name: "What the player sees" });
      expect(within(strip).getByRole("meter", { name: "Health" })).toHaveAttribute("aria-valuenow", "7");
    });

    it("is absent when nothing is shown to the player", async () => {
      await openStep({}, { lantern_oil: LANTERN_OIL });
      await screen.findByRole("article", { name: "Tracked value Lantern oil" });
      expect(screen.queryByRole("region", { name: "What the player sees" })).toBeNull();
    });
  });

  it("enables the status display before saving a value the player sees as a Number", async () => {
    const { api, user } = await openStep({}, { lantern_oil: { ...LANTERN_OIL, hidden: true } });
    const card = await screen.findByRole("article", { name: "Tracked value Lantern oil" });
    await user.selectOptions(within(card).getByLabelText("Player sees"), "Number");
    await waitFor(() => expect(savedSchema(api).lantern_oil.hidden).toBeUndefined(), WAIT);
    expect(savedSchema(api).lantern_oil.display).toBeUndefined();
    expect(api.toolPuts).toEqual([["status_hud"]]);
    expect(api.writeLog.indexOf("tools")).toBeLessThan(
      api.writeLog.findIndex((entry) => entry.startsWith("scenario:state_schema")),
    );
  });

  it("asks to turn the status display off after the last shown value is removed", async () => {
    const shown = {
      ...LANTERN_OIL,
      display: { kind: "meter", label: "Lantern oil", clamp_min: 0, clamp_max: 10 },
    };
    const { api, user } = await openStep({ enabledTools: ["status_hud"] }, { lantern_oil: shown });
    const card = await screen.findByRole("article", { name: "Tracked value Lantern oil" });
    await user.selectOptions(within(card).getByLabelText("Player sees"), "Hidden");
    expect(await screen.findByText("Turn off Status HUD too?", {}, WAIT)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Turn off" }));
    await waitFor(() => expect(api.toolPuts.at(-1)).toEqual([]), WAIT);
  });

  describe("changing the type of a value in use", () => {
    const usedInEnding = {
      endConditions: [
        buildEndConditionFixture({
          end_condition_id: "ending-1",
          outcome_title: "Trusted",
          condition_expression: { field: "trust", op: ">=", value: 8 },
        }),
      ],
    };
    const trust = { type: "number" as const, label: "Trust", min: 0, max: 10, initial: 5, description: "x" };

    it("asks first and keeps the type when cancelled", async () => {
      const { api, user } = await openStep(usedInEnding, { trust });
      const card = await screen.findByRole("article", { name: "Tracked value Trust" });
      await within(card).findByRole("button", { name: "Ending: Trusted" });
      await user.selectOptions(within(card).getByLabelText("Type"), "Yes / no");
      expect(await screen.findByText(/Trust is used in 1 place\. Changing its type/)).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Cancel" }));
      await new Promise((resolve) => setTimeout(resolve, 800));
      expect(savedSchema(api).trust.type).toBe("number");
    });

    it("changes the type after confirming and flags the comparison that no longer fits", async () => {
      const { api, user } = await openStep(usedInEnding, { trust });
      const card = await screen.findByRole("article", { name: "Tracked value Trust" });
      await within(card).findByRole("button", { name: "Ending: Trusted" });
      await user.selectOptions(within(card).getByLabelText("Type"), "Yes / no");
      await user.click(await screen.findByRole("button", { name: "Change type" }));
      await waitFor(() => expect(savedSchema(api).trust.type).toBe("boolean"), WAIT);
      expect(await within(card).findByText(/Trust no longer fits this comparison/)).toBeInTheDocument();
    });

    it("changes the type straight away when nothing uses the value", async () => {
      const { api, user } = await openStep({}, { trust });
      const card = await screen.findByRole("article", { name: "Tracked value Trust" });
      await user.selectOptions(within(card).getByLabelText("Type"), "Yes / no");
      await waitFor(() => expect(savedSchema(api).trust.type).toBe("boolean"), WAIT);
    });
  });
});
