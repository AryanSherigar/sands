import { screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useStudioStore } from "../../stores/studio.store";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { renderGuideStep } from "../../test/renderGuideStep";
import { buildEndConditionFixture, buildScenarioFixture } from "../../test/studioApiMock";
import { StepEndings } from "./StepEndings";

const WAIT = { timeout: 4000 };

const STATE_SCHEMA = {
  lantern_oil: { type: "number" as const, label: "Lantern oil", min: 0, max: 10, initial: 10 },
  has_key: { type: "boolean" as const, label: "Has the key", initial: false },
};

const openStep = (init: Parameters<typeof renderGuideStep>[1] = {}) =>
  renderGuideStep(<StepEndings />, {
    scenario: buildScenarioFixture({ mode: "master", state_schema: STATE_SCHEMA }),
    ...init,
  });

const ending = (id: string, title: string, priority: number, extra: object = {}) =>
  buildEndConditionFixture({ end_condition_id: id, outcome_title: title, priority, ...extra });

describe("StepEndings", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
  });

  it("shows the empty state and both add buttons", async () => {
    await openStep();
    expect(await screen.findByText(/No endings yet/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "+ Win ending" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "+ Lose ending" })).toBeInTheDocument();
  });

  it("adds a win ending and a lose ending as numbered cards", async () => {
    const { api, user } = await openStep();
    await user.click(screen.getByRole("button", { name: "+ Win ending" }));
    await user.click(await screen.findByRole("button", { name: "+ Lose ending" }));
    expect(await screen.findByRole("article", { name: "Ending 2" }, WAIT)).toBeInTheDocument();
    expect(api.endConditionWrites.map((write) => write.outcome_tag)).toEqual(["win", "lose"]);
    expect(api.endConditionWrites.map((write) => write.priority)).toEqual([0, 1]);
  });

  it("saves a new tracked value from an ending's Ends when right after the ending was added", async () => {
    const { api, user } = await openStep();
    await user.click(await screen.findByRole("button", { name: "+ Win ending" }));
    const card = await screen.findByRole("article", { name: "Ending 1" }, WAIT);

    await user.selectOptions(within(card).getByLabelText("Value"), "+ New tracked value");
    const form = within(card).getByRole("group", { name: "New tracked value" });
    await user.type(within(form).getByLabelText("Name"), "Mara trust");
    await user.click(within(form).getByRole("button", { name: "Add value" }));

    await waitFor(() => expect(Object.keys(api.scenario?.state_schema ?? {})).toContain("mara_trust"), WAIT);
    expect(useStudioStore.getState().hasEditConflict).toBe(false);
  });

  it("saves the title, the result and the secret flag", async () => {
    const { api, user } = await openStep({ endConditions: [ending("e1", "", 0)] });
    const card = await screen.findByRole("article", { name: "Ending 1" });
    await user.type(within(card).getByLabelText("Title"), "The tide takes her");
    await user.click(within(card).getByRole("radio", { name: "Lose" }));
    await user.click(within(card).getByRole("checkbox", { name: /Secret/ }));
    await waitFor(() => expect(api.endConditions[0]).toMatchObject({
      outcome_title: "The tide takes her",
      outcome_tag: "lose",
      is_secret: true,
    }), WAIT);
    expect(within(card).getByText("Hidden from your story page until a player finds it")).toBeInTheDocument();
  });

  it("builds Ends when as a sentence and stores the wording beside the expression", async () => {
    const { api, user } = await openStep({ endConditions: [ending("e1", "Lights out", 0)] });
    const card = await screen.findByRole("article", { name: "Ending 1" });
    await user.selectOptions(within(card).getByLabelText("Value"), "Lantern oil");
    await user.selectOptions(within(card).getByLabelText("Comparison"), "drops to");
    await user.type(within(card).getByLabelText("Amount"), "0");
    await waitFor(() => expect(api.endConditions[0].condition_expression).toEqual({ field: "lantern_oil", op: "<=", value: 0 }), WAIT);
    expect(api.endConditions[0].metadata).toMatchObject({ rows: [{ comparison: "drops_to" }], joiner: "and" });
  });

  it("saves What the player reads as the outcome text", async () => {
    const { api, user } = await openStep({ endConditions: [ending("e1", "Lights out", 0)] });
    const card = await screen.findByRole("article", { name: "Ending 1" });
    await user.type(within(card).getByLabelText("What the player reads (Ending 1)"), "The lantern dies.");
    await waitFor(() => expect(api.endConditions[0].outcome_text).toBe("The lantern dies."), WAIT);
  });

  it("copies a Question to Help into What the player reads", async () => {
    const { api, user } = await openStep({ endConditions: [ending("e1", "Lights out", 0)] });
    const card = await screen.findByRole("article", { name: "Ending 1" });
    await user.click(within(card).getByRole("button", { name: /Questions to help/i }));
    await user.click(await within(card).findByRole("button", { name: /The ending/i }));
    await user.type(await within(card).findByLabelText("What's the last line?"), "She never looked back.");
    await waitFor(() => expect(api.endConditions[0].outcome_text).toContain("She never looked back."), WAIT);
  });

  it("numbers the cards in priority order and explains the order", async () => {
    await openStep({ endConditions: [ending("e2", "Second", 1), ending("e1", "First", 0)] });
    const cards = await screen.findAllByRole("article");
    expect(cards.map((card) => card.getAttribute("aria-label"))).toEqual(["Ending 1", "Ending 2"]);
    expect(within(cards[0]).getByLabelText("Title")).toHaveValue("First");
    expect(screen.getByText("If two endings happen at once, the higher one wins.")).toBeInTheDocument();
  });

  it("moves an ending up and down and writes the new order", async () => {
    const { api, user } = await openStep({ endConditions: [ending("e1", "First", 0), ending("e2", "Second", 1)] });
    const second = await screen.findByRole("article", { name: "Ending 2" });
    await user.click(within(second).getByRole("button", { name: "Ending 2 options" }));
    await user.click(screen.getByRole("menuitem", { name: "Move up" }));
    await waitFor(() => expect(api.endingReorders).toEqual([["e2", "e1"]]), WAIT);
    await waitFor(() => expect(within(screen.getByRole("article", { name: "Ending 1" })).getByLabelText("Title")).toHaveValue("Second"), WAIT);
    const newSecond = screen.getByRole("article", { name: "Ending 2" });
    await user.click(within(newSecond).getByRole("button", { name: "Ending 2 options" }));
    expect(screen.queryByRole("menuitem", { name: "Move down" })).toBeNull();
    await user.click(screen.getByRole("menuitem", { name: "Move up" }));
    await waitFor(() => expect(api.endingReorders.at(-1)).toEqual(["e1", "e2"]), WAIT);
  });

  it("offers a drag handle on every card", async () => {
    await openStep({ endConditions: [ending("e1", "First", 0)] });
    expect(await screen.findByRole("button", { name: "Drag to reorder ending 1" })).toBeInTheDocument();
  });

  it("duplicates an ending after the last one", async () => {
    const { api, user } = await openStep({ endConditions: [ending("e1", "Lights out", 0, { outcome_text: "Dark." })] });
    const card = await screen.findByRole("article", { name: "Ending 1" });
    await user.click(within(card).getByRole("button", { name: "Ending 1 options" }));
    await user.click(screen.getByRole("menuitem", { name: "Duplicate" }));
    expect(await screen.findByRole("article", { name: "Ending 2" }, WAIT)).toBeInTheDocument();
    expect(api.endConditionWrites[0]).toMatchObject({ outcome_title: "Lights out (copy)", outcome_text: "Dark.", priority: 1 });
  });

  it("deletes an ending", async () => {
    const { api, user } = await openStep({ endConditions: [ending("e1", "Lights out", 0)] });
    const card = await screen.findByRole("article", { name: "Ending 1" });
    await user.click(within(card).getByRole("button", { name: "Ending 1 options" }));
    await user.click(screen.getByRole("menuitem", { name: "Delete" }));
    await waitFor(() => expect(api.endConditions).toHaveLength(0), WAIT);
  });

  it("lists Test this ending in the menu", async () => {
    const { user } = await openStep({ endConditions: [ending("e1", "Lights out", 0)] });
    const card = await screen.findByRole("article", { name: "Ending 1" });
    await user.click(within(card).getByRole("button", { name: "Ending 1 options" }));
    expect(screen.getByRole("menuitem", { name: "Test this ending" })).toBeInTheDocument();
  });

  it("allows two endings with the same condition", async () => {
    const same = { field: "has_key", op: "==", value: true };
    await openStep({
      endConditions: [ending("e1", "A", 0, { condition_expression: same }), ending("e2", "B", 1, { condition_expression: same })],
    });
    expect(await screen.findAllByRole("article")).toHaveLength(2);
  });

  it("flags a missing value but still saves the other fields without touching the condition", async () => {
    const stale = { field: "deleted_value", op: "<=", value: 1 };
    const { api, user } = await openStep({
      endConditions: [ending("e1", "Gone", 0, { condition_expression: stale })],
    });
    const card = await screen.findByRole("article", { name: "Ending 1" });
    expect(await within(card).findByText("Missing: Deleted value")).toBeInTheDocument();
    await user.type(within(card).getByLabelText("Title"), "!");
    await waitFor(() => expect(api.endConditions[0].outcome_title).toBe("Gone!"), WAIT);
    expect(api.endConditions[0].condition_expression).toEqual(stale);
    expect(api.endConditionWrites.every((write) => !("condition_expression" in write))).toBe(true);
  });

  it("gives a new ending a priority above every existing one, even after a delete left a gap", async () => {
    const { api, user } = await openStep({ endConditions: [ending("e1", "First", 0), ending("e3", "Third", 2)] });
    await screen.findByRole("article", { name: "Ending 2" });
    await user.click(screen.getByRole("button", { name: "+ Win ending" }));
    await waitFor(() => expect(api.endConditionWrites).toHaveLength(1), WAIT);
    expect(api.endConditionWrites[0].priority).toBe(3);
  });

  it("copies an ending above every existing priority", async () => {
    const { api, user } = await openStep({ endConditions: [ending("e1", "First", 0), ending("e3", "Third", 5)] });
    const card = await screen.findByRole("article", { name: "Ending 1" });
    await user.click(within(card).getByRole("button", { name: "Ending 1 options" }));
    await user.click(screen.getByRole("menuitem", { name: "Duplicate" }));
    await waitFor(() => expect(api.endConditionWrites).toHaveLength(1), WAIT);
    expect(api.endConditionWrites[0].priority).toBe(6);
  });

  it("does not rewrite an expression the builder cannot show", async () => {
    const mixed = {
      field: "has_key",
      op: "==",
      value: true,
      AND: { field: "lantern_oil", op: "<=", value: 1, OR: { field: "lantern_oil", op: ">=", value: 9 } },
    };
    const { api, user } = await openStep({
      endConditions: [ending("e1", "Mixed", 0, { condition_expression: mixed })],
    });
    const card = await screen.findByRole("article", { name: "Ending 1" });
    expect(within(card).getByText("This uses advanced logic — edit in full editor.")).toBeInTheDocument();
    await user.type(within(card).getByLabelText("Title"), "!");
    await waitFor(() => expect(api.endConditions[0].outcome_title).toBe("Mixed!"), WAIT);
    expect(api.endConditions[0].condition_expression).toEqual(mixed);
    expect(api.endConditionWrites.every((write) => !("condition_expression" in write))).toBe(true);
  });
});
