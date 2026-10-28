import { screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { buildEntityFixture } from "../../test/cardApiMock";
import { renderGuideStep } from "../../test/renderGuideStep";
import { buildInvariantFixture, buildScenarioFixture } from "../../test/studioApiMock";
import { StepHardLimits } from "./StepHardLimits";

const WAIT = { timeout: 4000 };

const STATE_SCHEMA = {
  health: { type: "number" as const, label: "Health", min: 0, max: 10, initial: 10 },
  max_health: { type: "number" as const, label: "Max health", min: 0, max: 10, initial: 10 },
  money: { type: "number" as const, label: "Money", min: 0, initial: 0 },
  in_the_chapel: { type: "boolean" as const, label: "In the chapel", initial: false },
  weapon_drawn: { type: "boolean" as const, label: "Weapon drawn", initial: false },
};

const GUARD = buildEntityFixture({
  entity_id: "guard-1",
  canonical_name: "Guard",
  attributes_schema: { courage: { type: "number", label: "Courage", min: 0, max: 5 } },
});

const openStep = (init: Parameters<typeof renderGuideStep>[1] = {}) =>
  renderGuideStep(<StepHardLimits />, {
    scenario: buildScenarioFixture({ mode: "master", state_schema: STATE_SCHEMA }),
    entities: [GUARD],
    ...init,
  });

const limit = (id: string, extra: object = {}) =>
  buildInvariantFixture({ invariant_id: id, label: "New hard limit", ...extra });

describe("StepHardLimits", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
  });

  it("starts empty and adds a hard limit applying to the player", async () => {
    const { api, user } = await openStep();
    expect(await screen.findByText(/No hard limits yet/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "+ Add a hard limit" }));
    expect(await screen.findByRole("article", { name: "Hard limit 1" }, WAIT)).toBeInTheDocument();
    expect(api.invariantWrites[0]).toMatchObject({ applies_to: "player", invariant_expression: {} });
  });

  it("compares a value to another value with a reference leaf", async () => {
    const { api, user } = await openStep({ invariants: [limit("l1")] });
    const card = await screen.findByRole("article", { name: "Hard limit 1" });
    await user.selectOptions(within(card).getByLabelText("Value"), "Health");
    await user.selectOptions(within(card).getByLabelText("Comparison"), "is at most");
    await user.selectOptions(within(card).getByLabelText("Compare to"), "another value");
    await user.selectOptions(within(card).getByLabelText("Other value"), "Max health");
    await waitFor(
      () => expect(api.invariants[0].invariant_expression).toEqual({ field: "health", op: "<=", ref: "max_health" }),
      WAIT,
    );
    expect(api.invariants[0].metadata).toMatchObject({ rows: [{ comparison: "at_most" }] });
  });

  it("offers a single row for a value-vs-value limit", async () => {
    await openStep({ invariants: [limit("l1")] });
    const card = await screen.findByRole("article", { name: "Hard limit 1" });
    expect(within(card).queryByRole("button", { name: "+ Add another" })).toBeNull();
  });

  it("compiles a while limit with the must-be wording", async () => {
    const { api, user } = await openStep({ invariants: [limit("l1")] });
    const card = await screen.findByRole("article", { name: "Hard limit 1" });
    await user.click(within(card).getByRole("radio", { name: "While something is true" }));
    const guard = within(card).getByRole("group", { name: "Row 1" });
    const must = within(card).getByRole("group", { name: "Row 2" });
    await user.selectOptions(within(guard).getByLabelText("Value"), "In the chapel");
    await user.selectOptions(within(guard).getByLabelText("Comparison"), "becomes yes");
    await user.selectOptions(within(must).getByLabelText("Value"), "Weapon drawn");
    const labels = within(within(must).getByLabelText("Comparison")).getAllByRole("option").map((option) => option.textContent);
    expect(labels).toEqual(["Choose…", "must be yes", "must be no"]);
    await user.selectOptions(within(must).getByLabelText("Comparison"), "must be no");
    await waitFor(
      () =>
        expect(api.invariants[0].invariant_expression).toEqual({
          field: "weapon_drawn",
          op: "==",
          value: false,
          OR: { NOT: { field: "in_the_chapel", op: "==", value: true } },
        }),
      WAIT,
    );
  });

  it("shows the while limit back from its saved expression", async () => {
    await openStep({
      invariants: [
        limit("l1", {
          narrator_text: "x",
          invariant_expression: {
            field: "weapon_drawn",
            op: "==",
            value: false,
            OR: { NOT: { field: "in_the_chapel", op: "==", value: true } },
          },
        }),
      ],
    });
    const card = await screen.findByRole("article", { name: "Hard limit 1" });
    expect(within(card).getByRole("radio", { name: "While something is true" })).toBeChecked();
    expect(within(within(card).getByRole("group", { name: "Row 2" })).getByLabelText("Comparison")).toHaveValue("becomes_no");
  });

  it("saves who it applies to: the player, everyone or a card", async () => {
    const { api, user } = await openStep({ invariants: [limit("l1", { narrator_text: "x" })] });
    const card = await screen.findByRole("article", { name: "Hard limit 1" });
    const applies = within(card).getByLabelText("Applies to");
    expect(within(applies).getAllByRole("option").map((option) => option.textContent)).toEqual([
      "The player",
      "Everyone",
      "Guard",
    ]);
    await user.selectOptions(applies, "Everyone");
    await waitFor(() => expect(api.invariants[0].applies_to).toBe("global"), WAIT);
    await user.selectOptions(applies, "Guard");
    await waitFor(() => expect(api.invariants[0].applies_to).toBe("guard-1"), WAIT);
  });

  it("scopes the value picker to what the limit applies to", async () => {
    const { user } = await openStep({ invariants: [limit("l1", { narrator_text: "x", applies_to: "global" })] });
    const card = await screen.findByRole("article", { name: "Hard limit 1" });
    const valueLabels = (): string[] =>
      within(within(card).getByLabelText("Value")).getAllByRole("option").map((option) => option.textContent ?? "");
    expect(valueLabels()).toContain("Health");
    expect(valueLabels()).not.toContain("Guard's Courage");
    await user.selectOptions(within(card).getByLabelText("Applies to"), "Guard");
    expect(valueLabels()).toContain("Guard's Courage");
    expect(valueLabels()).toContain("Health");
  });

  it("builds the In words suggestion by plain substitution and lets it be edited", async () => {
    const { api, user } = await openStep({ invariants: [limit("l1")] });
    const card = await screen.findByRole("article", { name: "Hard limit 1" });
    await user.selectOptions(within(card).getByLabelText("Value"), "Health");
    await user.selectOptions(within(card).getByLabelText("Comparison"), "is at most");
    await user.type(within(card).getByLabelText("Amount"), "8");
    const words = within(card).getByLabelText("In words");
    expect(words).toHaveValue("Always: Health is at most 8.");
    await waitFor(() => expect(api.invariants[0].narrator_text).toBe("Always: Health is at most 8."), WAIT);
    await user.clear(words);
    await user.type(words, "Health never tops 8.");
    await waitFor(() => expect(api.invariants[0].narrator_text).toBe("Health never tops 8."), WAIT);
  });

  it("hints when a limit only repeats a lowest or highest value", async () => {
    await openStep({
      invariants: [
        limit("l1", {
          narrator_text: "x",
          invariant_expression: { field: "money", op: ">=", value: 0 },
        }),
      ],
    });
    expect(await screen.findByText("Money's lowest value already does this.")).toBeInTheDocument();
  });

  it("copies an example in as a start and fills in the values that exist", async () => {
    const { api, user } = await openStep();
    await user.click(screen.getByRole("button", { name: "Health is at most Max health" }));
    await waitFor(() => expect(api.invariants).toHaveLength(1), WAIT);
    expect(api.invariants[0]).toMatchObject({
      narrator_text: "Health can never go above Max health.",
      invariant_expression: { field: "health", op: "<=", ref: "max_health" },
    });
    await user.click(screen.getByRole("button", { name: "While In the chapel is yes → Weapon drawn must be no" }));
    await waitFor(() => expect(api.invariants).toHaveLength(2), WAIT);
    expect(api.invariants[1].invariant_expression).toMatchObject({ OR: { NOT: { field: "in_the_chapel" } } });
    await user.click(screen.getByRole("button", { name: "While Time is Night → Shop open must be no" }));
    await waitFor(() => expect(api.invariants).toHaveLength(3), WAIT);
    expect(api.invariants[2].invariant_expression).toEqual({});
  });

  it("links words-only rules to Always remember in the World step", async () => {
    const { user } = await openStep();
    await user.click(screen.getByRole("button", { name: "Just a rule in words? Add it to Always remember." }));
    expect(useStudioTabsStore.getState().guideStep).toBe(5);
  });

  it("has duplicate and delete but no test action", async () => {
    const { api, user } = await openStep({ invariants: [limit("l1", { label: "Cap", narrator_text: "x" })] });
    const card = await screen.findByRole("article", { name: "Hard limit 1" });
    await user.click(within(card).getByRole("button", { name: "Hard limit 1 options" }));
    expect(screen.queryByRole("menuitem", { name: /Test/ })).toBeNull();
    await user.click(screen.getByRole("menuitem", { name: "Duplicate" }));
    await screen.findByRole("article", { name: "Hard limit 2" }, WAIT);
    expect(api.invariantWrites[0]).toMatchObject({ label: "Cap (copy)" });
    await user.click(within(screen.getByRole("article", { name: "Hard limit 2" })).getByRole("button", { name: "Hard limit 2 options" }));
    await user.click(screen.getByRole("menuitem", { name: "Delete" }));
    await waitFor(() => expect(api.invariants).toHaveLength(1), WAIT);
  });

  it("shows the full-editor notice for logic it cannot show and leaves it alone", async () => {
    const mixed = {
      field: "health",
      op: "<=",
      value: 3,
      AND: { field: "money", op: ">=", value: 1, OR: { field: "money", op: "<=", value: 9 } },
    };
    const { api, user } = await openStep({
      invariants: [limit("l1", { narrator_text: "words", invariant_expression: mixed })],
    });
    const card = await screen.findByRole("article", { name: "Hard limit 1" });
    expect(within(card).getByText("This uses advanced logic — edit in full editor.")).toBeInTheDocument();
    await user.selectOptions(within(card).getByLabelText("Applies to"), "Everyone");
    await waitFor(() => expect(api.invariants[0].applies_to).toBe("global"), WAIT);
    expect(api.invariants[0].invariant_expression).toEqual(mixed);
  });

  it("flags a missing value but still saves Applies to and leaves the condition alone", async () => {
    const stale = { field: "gone", op: "<=", value: 1 };
    const { api, user } = await openStep({
      invariants: [limit("l1", { narrator_text: "x", invariant_expression: stale })],
    });
    const card = await screen.findByRole("article", { name: "Hard limit 1" });
    expect(await within(card).findByText("Missing: Gone")).toBeInTheDocument();
    await user.selectOptions(within(card).getByLabelText("Applies to"), "Everyone");
    await waitFor(() => expect(api.invariants[0].applies_to).toBe("global"), WAIT);
    expect(api.invariants[0].invariant_expression).toEqual(stale);
    expect(api.invariantWrites.every((write) => !("invariant_expression" in write))).toBe(true);
  });

  it("lists the player once and only cards that have values", async () => {
    const player = buildEntityFixture({ entity_id: "player-1", canonical_name: "Mara", is_player: true });
    const empty = buildEntityFixture({ entity_id: "empty-1", canonical_name: "Crowd" });
    await openStep({ invariants: [limit("l1", { narrator_text: "x" })], entities: [player, empty, GUARD] });
    const card = await screen.findByRole("article", { name: "Hard limit 1" });
    const labels = within(within(card).getByLabelText("Applies to")).getAllByRole("option").map((option) => option.textContent);
    expect(labels).toEqual(["The player", "Everyone", "Guard"]);
  });

  it("keeps tracked values in the picker when the limit applies to a card", async () => {
    const { user } = await openStep({ invariants: [limit("l1", { narrator_text: "x" })] });
    const card = await screen.findByRole("article", { name: "Hard limit 1" });
    await user.selectOptions(within(card).getByLabelText("Applies to"), "Guard");
    const labels = within(within(card).getByLabelText("Value")).getAllByRole("option").map((option) => option.textContent);
    expect(labels).toEqual(expect.arrayContaining(["Health", "Guard's Courage"]));
  });

  it("marks In words as required and says so when it is empty", async () => {
    const { user } = await openStep({ invariants: [limit("l1")] });
    const card = await screen.findByRole("article", { name: "Hard limit 1" });
    expect(within(card).getByText("In words (required)")).toBeInTheDocument();
    await user.type(within(card).getByLabelText("In words"), "a");
    await user.clear(within(card).getByLabelText("In words"));
    expect(within(card).getByRole("alert")).toHaveTextContent("Say it in words");
  });
});
