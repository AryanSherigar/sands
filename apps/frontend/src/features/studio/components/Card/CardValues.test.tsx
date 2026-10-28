import { screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { buildEntityFixture, buildFactFixture } from "../../test/cardApiMock";
import { renderGuideStep } from "../../test/renderGuideStep";
import { STUDIO_TEST_SCENARIO_ID, buildScenarioFixture } from "../../test/studioApiMock";
import { SentenceBuilder } from "../SentenceBuilder/SentenceBuilder";
import { Card } from "./Card";

const WAIT = { timeout: 4000 };

const MARA = buildEntityFixture({ entity_id: "mara", canonical_name: "Mara" });
const LIGHTHOUSE = buildEntityFixture({
  entity_id: "lighthouse",
  canonical_name: "The Lighthouse",
  entity_type: "location",
});

const openCard = (
  mode: "master" | "newbie",
  init: Parameters<typeof renderGuideStep>[1] = {},
  entityId = "mara",
) =>
  renderGuideStep(<Card scenarioId={STUDIO_TEST_SCENARIO_ID} entityId={entityId} />, {
    scenario: buildScenarioFixture({ mode }),
    entities: [MARA, LIGHTHOUSE],
    ...init,
  });

const lastAttributes = (api: Awaited<ReturnType<typeof openCard>>["api"]): Record<string, Record<string, unknown>> =>
  api.entities.find((entity) => entity.entity_id === "mara")?.attributes_schema as never;

describe("Card values", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
  });

  it.each([
    ["character", "mara"],
    ["place", "lighthouse"],
  ])("shows a Values section on a %s card when Advanced mode is on", async (_kind, entityId) => {
    await openCard("master", {}, entityId);
    expect(await screen.findByRole("region", { name: "Values" })).toBeInTheDocument();
  });

  it.each([
    ["group", "faction"],
    ["thing", "item"],
  ])("shows a Values section on a %s card", async (_kind, entityType) => {
    const card = buildEntityFixture({ entity_id: "card-x", canonical_name: "Card X", entity_type: entityType });
    await openCard("master", { entities: [card] }, "card-x");
    expect(await screen.findByRole("region", { name: "Values" })).toBeInTheDocument();
  });

  it("hides the Values section when Advanced mode is off but keeps the stored values", async () => {
    const withTrust = buildEntityFixture({
      entity_id: "mara",
      canonical_name: "Mara",
      attributes_schema: { trust: { type: "number", label: "Trust", initial: 5 } },
    });
    const { api } = await openCard("newbie", { entities: [withTrust] });
    await screen.findByLabelText("Add a trigger");
    expect(screen.queryByRole("region", { name: "Values" })).toBeNull();
    expect(lastAttributes(api).trust).toMatchObject({ type: "number", label: "Trust" });
  });

  it("writes a new value into the card's attribute schema", async () => {
    const { api, user } = await openCard("master");
    const values = within(await screen.findByRole("region", { name: "Values" }));

    await user.type(values.getByLabelText("New value name"), "Trust");
    await user.click(values.getByRole("button", { name: "Add value" }));

    await waitFor(() => expect(lastAttributes(api).trust).toBeDefined(), WAIT);
    expect(lastAttributes(api).trust).toEqual({
      type: "number",
      label: "Trust",
      initial: 0,
      is_narrator_visible: false,
    });
  });

  it("saves lowest, highest and the narrator flag on a value", async () => {
    const withTrust = buildEntityFixture({
      entity_id: "mara",
      canonical_name: "Mara",
      attributes_schema: { trust: { type: "number", label: "Trust", initial: 5 } },
    });
    const { api, user } = await openCard("master", { entities: [withTrust] });
    const value = within(await screen.findByRole("article", { name: "Value Trust" }));

    await user.type(value.getByLabelText("Highest"), "10");
    await user.click(value.getByLabelText("The narrator always sees this"));

    await waitFor(() => expect(lastAttributes(api).trust.is_narrator_visible).toBe(true), WAIT);
    expect(lastAttributes(api).trust.max).toBe(10);
    expect(lastAttributes(api).trust.min).toBeUndefined();
  });

  it("appears in the value picker as the card's name and value", async () => {
    const withTrust = buildEntityFixture({
      entity_id: "mara",
      canonical_name: "Mara",
      attributes_schema: { trust: { type: "number", label: "Trust", initial: 5 } },
    });
    const { user } = await renderGuideStep(
      <SentenceBuilder value={null} onChange={() => undefined} />,
      { scenario: buildScenarioFixture({ mode: "master" }), entities: [withTrust] },
    );
    const picker = await screen.findByLabelText("Value");
    await waitFor(() => expect(within(picker).getByRole("option", { name: "Mara's Trust" })).toBeInTheDocument(), WAIT);
    await user.selectOptions(picker, "Mara's Trust");
    expect(screen.getByLabelText("Comparison")).toBeInTheDocument();
  });

  it("warns before deleting a value that a rule or ending uses", async () => {
    const withTrust = buildEntityFixture({
      entity_id: "mara",
      canonical_name: "Mara",
      attributes_schema: { trust: { type: "number", label: "Trust", initial: 5 } },
    });
    const { buildEndConditionFixture } = await import("../../test/studioApiMock");
    const ending = buildEndConditionFixture({
      end_condition_id: "e1",
      condition_expression: { field: "mara.trust", op: "<=", value: 0 },
    });
    const { user } = await openCard("master", { entities: [withTrust], endConditions: [ending] });
    const value = await screen.findByRole("article", { name: "Value Trust" });

    await user.click(within(value).getByRole("button", { name: "Trust options" }));
    await user.click(await screen.findByRole("menuitem", { name: "Delete" }));

    expect(await screen.findByText("Trust is used in 1 place. Delete anyway?")).toBeInTheDocument();
  });
});

describe("Card links in Advanced mode", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
  });

  const startAddLink = async (mode: "master" | "newbie") => {
    const view = await openCard(mode);
    await view.user.click(await screen.findByRole("button", { name: "Add link" }));
    return view;
  };

  it("sends exactly one far end: plain text as object_literal", async () => {
    const { api, user } = await startAddLink("master");
    await user.selectOptions(screen.getByLabelText("Link to a"), "text");
    await user.type(screen.getByLabelText("Plain text"), "70 years old");
    await user.type(screen.getByLabelText("How are they linked?"), "is");
    await user.click(screen.getByRole("button", { name: "Save link" }));

    await waitFor(() => expect(api.factCreates).toHaveLength(1), WAIT);
    expect(api.factCreates[0]).toMatchObject({
      subject_entity_id: "mara",
      predicate: "is",
      object_literal: "70 years old",
    });
    expect(api.factCreates[0]).not.toHaveProperty("object_entity_id");
  });

  it("sends the card as object_entity_id when linking to a card", async () => {
    const { api, user } = await startAddLink("master");
    await user.selectOptions(screen.getByLabelText("Link to"), "The Lighthouse");
    await user.type(screen.getByLabelText("How are they linked?"), "lives in");
    await user.click(screen.getByRole("button", { name: "Save link" }));

    await waitFor(() => expect(api.factCreates).toHaveLength(1), WAIT);
    expect(api.factCreates[0]).toMatchObject({
      subject_entity_id: "mara",
      predicate: "lives in",
      object_entity_id: "lighthouse",
    });
    expect(api.factCreates[0]).not.toHaveProperty("object_literal");
  });

  it("offers plain text and only when only in Advanced mode", async () => {
    await startAddLink("newbie");
    expect(screen.queryByLabelText("Link to a")).toBeNull();
    expect(screen.queryByRole("button", { name: "+ Only when…" })).toBeNull();
  });

  it("compiles only when into the link's when_active", async () => {
    const { api, user } = await openCard("master", {
      scenario: buildScenarioFixture({
        mode: "master",
        state_schema: { trust: { type: "number", label: "Trust", min: 0, max: 10, initial: 5 } },
      }),
    });
    await user.click(await screen.findByRole("button", { name: "Add link" }));
    await user.selectOptions(screen.getByLabelText("Link to"), "The Lighthouse");
    await user.type(screen.getByLabelText("How are they linked?"), "lives in");
    await user.click(screen.getByRole("button", { name: "+ Only when…" }));
    await user.selectOptions(await screen.findByLabelText("Value"), "Trust");
    await user.selectOptions(screen.getByLabelText("Comparison"), "is at least");
    await user.type(screen.getByLabelText("Amount"), "8");
    await user.click(screen.getByRole("button", { name: "Save link" }));

    await waitFor(() => expect(api.factCreates).toHaveLength(1), WAIT);
    expect(api.factCreates[0]).toMatchObject({
      object_entity_id: "lighthouse",
      when_active: { field: "trust", op: ">=", value: 8 },
    });
  });

  it("lists a plain-text link in Advanced mode and hides it when Advanced is off", async () => {
    const textLink = buildFactFixture({
      fact_id: "f1",
      subject_entity_id: "mara",
      predicate: "is",
      object_entity_id: null as never,
      object_literal: "70 years old",
    });
    const on = await openCard("master", { facts: [textLink] });
    expect(await screen.findByText("70 years old")).toBeInTheDocument();
    on.unmount();

    await openCard("newbie", { facts: [textLink] });
    await screen.findByLabelText("Add a trigger");
    expect(screen.queryByText("70 years old")).toBeNull();
  });

  it("shows the full-editor notice, not a rewritten builder, for a stored only-when it cannot read", async () => {
    const odd = buildFactFixture({
      fact_id: "f2",
      subject_entity_id: "mara",
      predicate: "knows",
      object_entity_id: "lighthouse",
      when_active: { legacy: "shape" },
    });
    const { api } = await openCard("master", { facts: [odd] });

    expect(await screen.findByText(/This uses advanced logic/)).toBeInTheDocument();
    expect(api.factUpdates).toEqual([]);
  });
});
