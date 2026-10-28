import { screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { renderGuideStep } from "../../test/renderGuideStep";
import { buildConditionFixture, buildScenarioFixture } from "../../test/studioApiMock";
import { StepRules } from "./StepRules";

const WAIT = { timeout: 4000 };

const STATE_SCHEMA = {
  lantern_oil: { type: "number" as const, label: "Lantern oil", min: 0, max: 10, initial: 10 },
  sanity: { type: "number" as const, label: "Sanity", min: 0, max: 10, initial: 10 },
  trust: { type: "number" as const, label: "Trust", min: 0, max: 10, initial: 5 },
  has_key: { type: "boolean" as const, label: "Has the key", initial: false },
};

const openStep = (init: Parameters<typeof renderGuideStep>[1] = {}) =>
  renderGuideStep(<StepRules />, {
    scenario: buildScenarioFixture({ mode: "master", state_schema: STATE_SCHEMA }),
    ...init,
  });

const rule = (id: string, extra: object = {}) =>
  buildConditionFixture({ condition_id: id, label: "New rule", ...extra });

describe("StepRules", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
  });

  it("starts empty and adds a rule card", async () => {
    const { api, user } = await openStep();
    expect(await screen.findByText(/No rules yet/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "+ Add a rule" }));
    expect(await screen.findByRole("article", { name: "Rule 1" }, WAIT)).toBeInTheDocument();
    expect(api.conditionWrites[0]).toMatchObject({ is_one_shot: false, narrator_instruction: "" });
  });

  it("builds When as a sentence and names the rule from it", async () => {
    const { api, user } = await openStep({
      conditions: [rule("r1", { narrator_instruction: "Go dark." })],
    });
    const card = await screen.findByRole("article", { name: "Rule 1" });
    await user.selectOptions(within(card).getByLabelText("Value"), "Lantern oil");
    await user.selectOptions(within(card).getByLabelText("Comparison"), "is at most");
    await user.type(within(card).getByLabelText("Amount"), "2");
    await waitFor(() => expect(api.conditions[0].label).toBe("When Lantern oil is at most 2"), WAIT);
    expect(api.conditions[0].condition_expression).toEqual({ field: "lantern_oil", op: "<=", value: 2 });
    expect(api.conditions[0].metadata).toMatchObject({ rows: [{ comparison: "at_most" }], joiner: "and" });
    expect(within(card).getByLabelText("Title")).toHaveAttribute("placeholder", "When Lantern oil is at most 2");
  });

  it("keeps a title the creator typed", async () => {
    const { api, user } = await openStep({ conditions: [rule("r1", { narrator_instruction: "x" })] });
    const card = await screen.findByRole("article", { name: "Rule 1" });
    await user.type(within(card).getByLabelText("Title"), "Trouble");
    await waitFor(() => expect(api.conditions[0].label).toBe("Trouble"), WAIT);
  });

  it("chooses how often with the explanation", async () => {
    const { api, user } = await openStep({ conditions: [rule("r1", { narrator_instruction: "x" })] });
    const card = await screen.findByRole("article", { name: "Rule 1" });
    expect(within(card).getByRole("radio", { name: "Every turn while this is true" })).toBeChecked();
    expect(within(card).getByText(/lowers Sanity will lower it every turn/)).toBeInTheDocument();
    await user.click(within(card).getByRole("radio", { name: "Only once, the first time" }));
    await waitFor(() => expect(api.conditions[0].is_one_shot).toBe(true), WAIT);
  });

  it("saves Tell the narrator", async () => {
    const { api, user } = await openStep({ conditions: [rule("r1")] });
    const card = await screen.findByRole("article", { name: "Rule 1" });
    await user.type(within(card).getByLabelText("Tell the narrator"), "Mara shares her secret");
    await waitFor(() => expect(api.conditions[0].narrator_instruction).toBe("Mara shares her secret"), WAIT);
  });

  it("changes a value by going down by an amount", async () => {
    const { api, user } = await openStep({ conditions: [rule("r1")] });
    const card = await screen.findByRole("article", { name: "Rule 1" });
    await user.click(within(card).getByRole("button", { name: "+ Change a value" }));
    const change = within(card).getByRole("group", { name: "Change 1" });
    await user.selectOptions(within(change).getByLabelText("Value to change"), "Sanity");
    await user.selectOptions(within(change).getByLabelText("How it changes"), "goes down by");
    await user.type(within(change).getByLabelText("Amount"), "1");
    await waitFor(
      () => expect(api.conditions[0].state_mutations).toEqual([{ path: "sanity", op: "decrement", value: 1 }]),
      WAIT,
    );
  });

  it("asks for what happens and does not save a rule with an empty Then", async () => {
    const { api, user } = await openStep({ conditions: [rule("r1")] });
    const card = await screen.findByRole("article", { name: "Rule 1" });
    await user.selectOptions(within(card).getByLabelText("Value"), "Lantern oil");
    await user.selectOptions(within(card).getByLabelText("Comparison"), "is at most");
    await user.type(within(card).getByLabelText("Amount"), "2");
    expect(await within(card).findByText("Add what happens")).toBeInTheDocument();
    await new Promise((resolve) => setTimeout(resolve, 900));
    expect(api.conditionWrites).toEqual([]);
    await user.type(within(card).getByLabelText("Tell the narrator"), "Go dark");
    await waitFor(() => expect(api.conditions[0].narrator_instruction).toBe("Go dark"), WAIT);
    expect(api.conditions[0].condition_expression).toEqual({ field: "lantern_oil", op: "<=", value: 2 });
    expect(within(card).queryByText("Add what happens")).toBeNull();
  });

  it("warns when an every-turn rule changes the value it checks", async () => {
    await openStep({
      conditions: [
        rule("r1", {
          condition_expression: { field: "sanity", op: "<=", value: 5 },
          state_mutations: [{ path: "sanity", op: "decrement", value: 1 }],
        }),
      ],
    });
    expect(
      await screen.findByText("This will repeat every turn until Sanity is 0. Is that what you want?"),
    ).toBeInTheDocument();
  });

  it("does not warn for a rule that only fires once", async () => {
    await openStep({
      conditions: [
        rule("r1", {
          is_one_shot: true,
          condition_expression: { field: "sanity", op: "<=", value: 5 },
          state_mutations: [{ path: "sanity", op: "decrement", value: 1 }],
        }),
      ],
    });
    await screen.findByRole("article", { name: "Rule 1" });
    expect(screen.queryByText(/This will repeat every turn/)).toBeNull();
  });

  it("copies an example in as a start, filling in the values that exist", async () => {
    const { api, user } = await openStep();
    await user.click(
      screen.getByRole("button", { name: "When Trust is at least 8 → Tell the narrator: Mara shares her secret" }),
    );
    await waitFor(() => expect(api.conditions).toHaveLength(1), WAIT);
    expect(api.conditions[0]).toMatchObject({
      label: "When Trust is at least 8",
      narrator_instruction: "Mara shares her secret.",
      condition_expression: { field: "trust", op: ">=", value: 8 },
      is_one_shot: false,
    });
  });

  it("copies an example as text only when its values do not exist yet", async () => {
    const { api, user } = await openStep();
    await user.click(
      screen.getByRole("button", {
        name: "Only once, when Has the key becomes yes → Tell the narrator: the lighthouse door unlocks",
      }),
    );
    await waitFor(() => expect(api.conditions).toHaveLength(1), WAIT);
    expect(api.conditions[0]).toMatchObject({ is_one_shot: true, condition_expression: { field: "has_key", op: "==", value: true } });
    await user.click(screen.getByRole("button", { name: "When Time becomes Night → Health goes down by 1 each turn" }));
    await waitFor(() => expect(api.conditions).toHaveLength(2), WAIT);
    expect(api.conditions[1].condition_expression).toEqual({});
    expect(api.conditions[1].label).toBe("When Time becomes Night");
  });

  it("switches the sound tool on before saving a sound, and offers to turn it off again", async () => {
    const { api, user } = await openStep({
      conditions: [rule("r1", { narrator_instruction: "x" })],
      enabledTools: [],
    });
    const card = await screen.findByRole("article", { name: "Rule 1" });
    await user.click(within(card).getByRole("button", { name: "+ Sound" }));
    await user.selectOptions(within(card).getByLabelText("Sound cue"), "phone_ring");
    await waitFor(() => expect(api.conditions[0].sensory_cue).toBe("phone_ring"), WAIT);
    expect(api.toolPuts).toEqual([["atmosphere"]]);
    expect(api.scenario?.enabled_tools).toEqual(["status_hud", "atmosphere"]);
    expect(api.writeLog.indexOf("tools")).toBeGreaterThanOrEqual(0);

    await user.selectOptions(within(card).getByLabelText("Sound cue"), "");
    expect(await screen.findByText("Turn off Atmosphere too?", {}, WAIT)).toBeInTheDocument();
  });

  it("does not switch the sound tool on again when it is already on", async () => {
    const { api, user } = await openStep({
      conditions: [rule("r1", { narrator_instruction: "x" })],
      enabledTools: ["status_hud", "atmosphere"],
    });
    const card = await screen.findByRole("article", { name: "Rule 1" });
    await user.click(within(card).getByRole("button", { name: "+ Sound" }));
    await user.selectOptions(within(card).getByLabelText("Sound cue"), "phone_ring");
    await waitFor(() => expect(api.conditions[0].sensory_cue).toBe("phone_ring"), WAIT);
    expect(api.toolPuts).toEqual([]);
  });

  it("duplicates, tests and deletes from the menu", async () => {
    const { api, user } = await openStep({ conditions: [rule("r1", { label: "Warn", narrator_instruction: "x" })] });
    const card = await screen.findByRole("article", { name: "Rule 1" });
    await user.click(within(card).getByRole("button", { name: "Rule 1 options" }));
    expect(screen.getByRole("menuitem", { name: "Test this rule" })).toBeInTheDocument();
    await user.click(screen.getByRole("menuitem", { name: "Duplicate" }));
    expect(await screen.findByRole("article", { name: "Rule 2" }, WAIT)).toBeInTheDocument();
    expect(api.conditionWrites[0]).toMatchObject({ label: "Warn (copy)", narrator_instruction: "x" });
    await user.click(within(screen.getByRole("article", { name: "Rule 2" })).getByRole("button", { name: "Rule 2 options" }));
    await user.click(screen.getByRole("menuitem", { name: "Delete" }));
    await waitFor(() => expect(api.conditions).toHaveLength(1), WAIT);
  });

  it("flags a missing condition value but still saves the other fields", async () => {
    const stale = { field: "gone", op: "<=", value: 1 };
    const { api, user } = await openStep({
      conditions: [rule("r1", { narrator_instruction: "x", condition_expression: stale })],
    });
    const card = await screen.findByRole("article", { name: "Rule 1" });
    expect(await within(card).findByText("Missing: Gone")).toBeInTheDocument();
    await user.type(within(card).getByLabelText("Tell the narrator"), "y");
    await waitFor(() => expect(api.conditions[0].narrator_instruction).toBe("xy"), WAIT);
    expect(api.conditions[0].condition_expression).toEqual(stale);
    expect(api.conditionWrites.every((write) => !("condition_expression" in write))).toBe(true);
  });

  it("shows a Change row whose value was deleted as Missing and does not rewrite the changes", async () => {
    const stale = [{ path: "lantern_oil_gone", op: "decrement", value: 1 }];
    const { api, user } = await openStep({
      conditions: [rule("r1", { narrator_instruction: "x", state_mutations: stale })],
    });
    const card = await screen.findByRole("article", { name: "Rule 1" });
    const change = within(card).getByRole("group", { name: "Change 1" });
    expect(within(change).getByText("Missing: Lantern oil gone")).toBeInTheDocument();
    await user.type(within(card).getByLabelText("Tell the narrator"), "y");
    await waitFor(() => expect(api.conditions[0].narrator_instruction).toBe("xy"), WAIT);
    expect(api.conditions[0].state_mutations).toEqual(stale);
    await user.click(within(change).getByRole("button", { name: "Remove change 1" }));
    await waitFor(() => expect(api.conditions[0].state_mutations).toEqual([]), WAIT);
  });

  it("sends a rule on a text value to the full editor instead of calling the value missing", async () => {
    const mood = { field: "mood", op: "==", value: "calm" };
    const stored = [{ path: "mood", op: "set", value: "calm" }];
    const { api, user } = await openStep({
      scenario: buildScenarioFixture({
        mode: "master",
        state_schema: { ...STATE_SCHEMA, mood: { type: "string" as const, label: "Mood", initial: "calm" } },
      }),
      conditions: [rule("r1", { narrator_instruction: "x", condition_expression: mood, state_mutations: stored })],
    });
    const card = await screen.findByRole("article", { name: "Rule 1" });
    expect(await within(card).findByRole("note")).toHaveTextContent("This uses advanced logic — edit in full editor.");
    expect(within(card).queryByText(/^Missing:/)).toBeNull();
    const change = within(card).getByRole("group", { name: "Change 1" });
    expect(within(change).getByText("This uses advanced logic — edit in full editor.")).toBeInTheDocument();
    await user.type(within(card).getByLabelText("Tell the narrator"), "y");
    await waitFor(() => expect(api.conditions[0].narrator_instruction).toBe("xy"), WAIT);
    expect(api.conditions[0].condition_expression).toEqual(mood);
    expect(api.conditions[0].state_mutations).toEqual(stored);
    expect(api.conditionWrites.every((write) => !("state_mutations" in write))).toBe(true);
  });

  it("keeps a legacy rule that only has a client effect editable", async () => {
    const { api, user } = await openStep({
      conditions: [
        rule("r1", { label: "Phone", metadata: { client_effect: { kind: "phone" } }, narrator_instruction: "" }),
      ],
    });
    const card = await screen.findByRole("article", { name: "Rule 1" });
    expect(within(card).queryByText("Add what happens")).toBeNull();
    await user.click(within(card).getByRole("radio", { name: "Only once, the first time" }));
    await waitFor(() => expect(api.conditions[0].is_one_shot).toBe(true), WAIT);
  });

  it("keeps a title that was typed as New rule", async () => {
    const { api, user } = await openStep({ conditions: [rule("r1", { narrator_instruction: "x" })] });
    const card = await screen.findByRole("article", { name: "Rule 1" });
    await user.type(within(card).getByLabelText("Title"), "New rule");
    await waitFor(() => expect(api.conditions[0].metadata).toMatchObject({ custom_title: true }), WAIT);
    expect(within(card).getByLabelText("Title")).toHaveValue("New rule");
  });

  it("starts a rule that has no typed title with an empty Title", async () => {
    await openStep({ conditions: [rule("r1", { narrator_instruction: "x" })] });
    const card = await screen.findByRole("article", { name: "Rule 1" });
    expect(within(card).getByLabelText("Title")).toHaveValue("");
  });
});
