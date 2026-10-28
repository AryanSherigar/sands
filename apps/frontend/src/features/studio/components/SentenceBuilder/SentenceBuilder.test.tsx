import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import React, { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { SentenceOutput } from "../../lib/sentenceRows";
import { server } from "@/test/msw/server";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { buildEntityFixture } from "../../test/cardApiMock";
import { createGuideWrapper } from "../../test/guideHookWrapper";
import { STUDIO_TEST_SCENARIO_ID, buildScenarioFixture, installStudioApi } from "../../test/studioApiMock";
import type { FieldExpression } from "../ConditionEditor/ExpressionBuilder/ExpressionBuilder.types";
import { SentenceBuilder } from "./SentenceBuilder";
import type { SentenceBuilderProps } from "./SentenceBuilder.types";

const WAIT = { timeout: 4000 };

const STATE_SCHEMA = {
  lantern_oil: { type: "number" as const, label: "Lantern oil", min: 0, max: 10, initial: 10 },
  has_key: { type: "boolean" as const, label: "Has the key", initial: false },
  time: { type: "enum" as const, label: "Time", options: ["Dawn", "Day", "Dusk", "Night"], initial: "Dawn" },
};

type HarnessProps = Partial<Omit<SentenceBuilderProps, "onChange">> & {
  onOutput: (next: SentenceOutput | null) => void;
};

const Harness: React.FC<HarnessProps> = ({ onOutput, value: initialValue = null, metadata: initialMetadata, ...rest }) => {
  const [value, setValue] = useState<FieldExpression | null>(initialValue);
  const [metadata, setMetadata] = useState(initialMetadata);
  return (
    <SentenceBuilder
      {...rest}
      value={value}
      metadata={metadata}
      onChange={(next) => {
        setValue(next?.expression ?? null);
        setMetadata(next?.metadata);
        onOutput(next);
      }}
    />
  );
};

const renderBuilder = async (props: Partial<HarnessProps> = {}, init: Parameters<typeof installStudioApi>[0] = {}) => {
  const api = installStudioApi({
    scenario: buildScenarioFixture({ mode: "master", state_schema: STATE_SCHEMA }),
    ...init,
  });
  const onOutput = vi.fn();
  const { Wrapper, queryClient } = createGuideWrapper();
  const user = userEvent.setup();
  render(<Harness onOutput={onOutput} {...props} />, { wrapper: Wrapper });
  await waitFor(
    () => expect(queryClient.getQueryData(["scenario", STUDIO_TEST_SCENARIO_ID])).toBeDefined(),
    WAIT,
  );
  return { api, onOutput, user };
};

const optionLabels = (select: HTMLElement): string[] =>
  within(select).getAllByRole("option").map((option) => option.textContent ?? "");

const lastOutput = (onOutput: ReturnType<typeof vi.fn>): SentenceOutput | null =>
  onOutput.mock.calls.at(-1)?.[0] ?? null;

describe("SentenceBuilder", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
  });

  describe("comparisons", () => {
    it("lists plain-word comparisons for a number", async () => {
      const { user } = await renderBuilder();
      await user.selectOptions(screen.getByLabelText("Value"), "Lantern oil");
      expect(optionLabels(screen.getByLabelText("Comparison")).slice(1)).toEqual([
        "drops to",
        "rises to",
        "is at least",
        "is at most",
        "is exactly",
      ]);
      expect(screen.getByLabelText("Amount")).toBeInTheDocument();
    });

    it("lists yes and no for a yes/no value, with no amount", async () => {
      const { user } = await renderBuilder();
      await user.selectOptions(screen.getByLabelText("Value"), "Has the key");
      expect(optionLabels(screen.getByLabelText("Comparison")).slice(1)).toEqual(["becomes yes", "becomes no"]);
      expect(screen.queryByLabelText("Amount")).toBeNull();
    });

    it("offers becomes plus the choices for a choice value", async () => {
      const { user } = await renderBuilder();
      await user.selectOptions(screen.getByLabelText("Value"), "Time");
      expect(optionLabels(screen.getByLabelText("Comparison")).slice(1)).toEqual(["becomes"]);
      expect(optionLabels(screen.getByLabelText("Choice")).slice(1)).toEqual(["Dawn", "Day", "Dusk", "Night"]);
    });
  });

  describe("compiling", () => {
    it("emits the expression and the wording once the row is complete, and previews it", async () => {
      const { user, onOutput } = await renderBuilder();
      await user.selectOptions(screen.getByLabelText("Value"), "Lantern oil");
      expect(onOutput).not.toHaveBeenCalled();
      await user.selectOptions(screen.getByLabelText("Comparison"), "drops to");
      expect(onOutput).not.toHaveBeenCalled();
      await user.type(screen.getByLabelText("Amount"), "2");

      expect(lastOutput(onOutput)).toEqual({
        expression: { field: "lantern_oil", op: "<=", value: 2 },
        metadata: { rows: [{ comparison: "drops_to" }], joiner: "and" },
      });
      expect(screen.getByText("Lantern oil drops to 2")).toBeInTheDocument();
    });

    it("shows one joiner for two rows, recompiles when it changes and updates the preview", async () => {
      const { user, onOutput } = await renderBuilder({
        value: { field: "lantern_oil", op: "<=", value: 2 },
        metadata: { rows: [{ comparison: "at_most" }], joiner: "and" },
      });
      expect(screen.queryByLabelText("Join rows with")).toBeNull();

      await user.click(screen.getByRole("button", { name: "+ Add another" }));
      const second = screen.getByRole("group", { name: "Row 2" });
      await user.selectOptions(within(second).getByLabelText("Value"), "Has the key");
      await user.selectOptions(within(second).getByLabelText("Comparison"), "becomes yes");

      expect(screen.getAllByLabelText("Join rows with")).toHaveLength(1);
      expect(lastOutput(onOutput)?.expression).toEqual({
        field: "lantern_oil",
        op: "<=",
        value: 2,
        AND: { field: "has_key", op: "==", value: true },
      });
      expect(screen.getByText("Lantern oil is at most 2 and Has the key is yes")).toBeInTheDocument();

      await user.selectOptions(screen.getByLabelText("Join rows with"), "or");

      expect(lastOutput(onOutput)?.expression).toMatchObject({ OR: { field: "has_key" } });
      expect(screen.getByText("Lantern oil is at most 2 or Has the key is yes")).toBeInTheDocument();
    });

    it("restores the creator's wording from the saved metadata", async () => {
      await renderBuilder({
        value: { field: "lantern_oil", op: "<=", value: 2 },
        metadata: { rows: [{ comparison: "drops_to" }], joiner: "and" },
      });
      expect(screen.getByLabelText("Comparison")).toHaveValue("drops_to");
      expect(screen.getByLabelText("Amount")).toHaveValue(2);
    });

    it("removes a row and recompiles the rest", async () => {
      const { user, onOutput } = await renderBuilder({
        value: { field: "lantern_oil", op: "<=", value: 2, AND: { field: "has_key", op: "==", value: true } },
      });

      await user.click(within(screen.getByRole("group", { name: "Row 2" })).getByRole("button", { name: "Remove row" }));

      expect(lastOutput(onOutput)?.expression).toEqual({ field: "lantern_oil", op: "<=", value: 2 });
    });

    it("compiles a while limit as the guard and must pair", async () => {
      const { user, onOutput } = await renderBuilder({ mode: "while-limit" });
      const [guard, must] = [screen.getByRole("group", { name: "Row 1" }), screen.getByRole("group", { name: "Row 2" })];
      await user.selectOptions(within(guard).getByLabelText("Value"), "Has the key");
      await user.selectOptions(within(guard).getByLabelText("Comparison"), "becomes yes");
      await user.selectOptions(within(must).getByLabelText("Value"), "Lantern oil");
      await user.selectOptions(within(must).getByLabelText("Comparison"), "must be at least");
      await user.type(within(must).getByLabelText("Amount"), "1");

      expect(lastOutput(onOutput)?.expression).toEqual({
        field: "lantern_oil",
        op: ">=",
        value: 1,
        OR: { NOT: { field: "has_key", op: "==", value: true } },
      });
      expect(screen.queryByLabelText("Join rows with")).toBeNull();
    });

    it("only offers the values the scope filter allows", async () => {
      await renderBuilder({ scopeFilter: (option) => option.kind === "boolean" });
      expect(optionLabels(screen.getByLabelText("Value"))).not.toContain("Lantern oil");
      expect(optionLabels(screen.getByLabelText("Value"))).toContain("Has the key");
    });

    it("offers card values by the card's name", async () => {
      await renderBuilder(
        {},
        {
          entities: [
            buildEntityFixture({
              entity_id: "guard-1",
              canonical_name: "Guard",
              attributes_schema: { health: { type: "number", label: "Health" } },
            }),
          ],
        },
      );
      await screen.findByRole("option", { name: "Guard's Health" }, WAIT);
    });
  });

  describe("new tracked value", () => {
    it("creates the value inline, selects it and saves it without a meaning yet", async () => {
      const { api, user } = await renderBuilder();

      await user.selectOptions(screen.getByLabelText("Value"), "+ New tracked value");
      const form = screen.getByRole("group", { name: "New tracked value" });
      await user.type(within(form).getByLabelText("Name"), "Mara trust");
      await user.click(within(form).getByRole("button", { name: "Add value" }));

      await waitFor(() => expect(screen.queryByRole("group", { name: "New tracked value" })).toBeNull(), WAIT);
      const saved = api.scenarioUpdates.at(-1)?.state_schema as Record<string, Record<string, unknown>>;
      expect(saved.mara_trust).toMatchObject({ type: "number", label: "Mara trust", min: 0, max: 10, initial: 0 });
      expect(saved.mara_trust.description).toBeUndefined();
      expect(saved.lantern_oil).toBeDefined();
      await waitFor(() => expect(screen.getByLabelText("Value")).toHaveValue("mara_trust"), WAIT);
      expect(optionLabels(screen.getByLabelText("Comparison")).slice(1)).toHaveLength(5);
    });

    it("keeps the form on its own row when an earlier row is removed", async () => {
      const { user } = await renderBuilder({
        value: { field: "lantern_oil", op: "<=", value: 2, AND: { field: "has_key", op: "==", value: true } },
      });
      const second = screen.getByRole("group", { name: "Row 2" });
      await user.selectOptions(within(second).getByLabelText("Value"), "+ New tracked value");

      await user.click(within(screen.getByRole("group", { name: "Row 1" })).getByRole("button", { name: "Remove row" }));

      expect(screen.getByRole("group", { name: "New tracked value" })).toBeInTheDocument();
    });

    it("keeps the row empty when the creator cancels", async () => {
      const { api, user } = await renderBuilder();

      await user.selectOptions(screen.getByLabelText("Value"), "+ New tracked value");
      await user.click(screen.getByRole("button", { name: "Cancel" }));

      expect(screen.queryByRole("group", { name: "New tracked value" })).toBeNull();
      expect(screen.getByLabelText("Value")).toHaveValue("");
      expect(api.scenarioUpdates).toHaveLength(0);
    });
  });

  describe("advanced logic", () => {
    const MIXED: FieldExpression = {
      field: "lantern_oil",
      op: "<=",
      value: 2,
      AND: { field: "has_key", op: "==", value: true, OR: { field: "time", op: "==", value: "Night" } },
    };

    it("shows the full-editor notice and never rewrites an expression it cannot show", async () => {
      const onOpenFullEditor = vi.fn();
      const { user, onOutput } = await renderBuilder({ value: MIXED, onOpenFullEditor });

      expect(screen.getByText("This uses advanced logic — edit in full editor.")).toBeInTheDocument();
      expect(screen.queryByLabelText("Value")).toBeNull();
      await user.click(screen.getByRole("button", { name: "Edit in full editor" }));
      await user.keyboard("{Tab}{Enter}");

      expect(onOpenFullEditor).toHaveBeenCalled();
      expect(onOutput).not.toHaveBeenCalled();
    });

    it("treats an operator the builder does not know the same way", async () => {
      const { onOutput } = await renderBuilder({ value: { field: "time", op: "matches", value: "Nig" } });
      expect(screen.getByText("This uses advanced logic — edit in full editor.")).toBeInTheDocument();
      expect(onOutput).not.toHaveBeenCalled();
    });
  });

  describe("loading and empty values", () => {
    it("shows no missing text and no validity signal until the cards have loaded", async () => {
      const onValidityChange = vi.fn();
      const guard = buildEntityFixture({
        entity_id: "guard-1",
        canonical_name: "Guard",
        attributes_schema: { health: { type: "number", label: "Health" } },
      });
      server.use(
        http.get("*/v1/scenarios/scenario-1/entities", async () => {
          await new Promise((resolve) => setTimeout(resolve, 300));
          return HttpResponse.json({ items: [guard] });
        }),
      );
      await renderBuilder(
        { value: { field: "guard-1.health", op: "<=", value: 2 }, onValidityChange },
        { entities: [guard] },
      );

      expect(screen.queryByText(/^Missing:/)).toBeNull();
      expect(onValidityChange).not.toHaveBeenCalledWith(false);
      await waitFor(() => expect(onValidityChange).toHaveBeenLastCalledWith(true), WAIT);
      expect(screen.queryByText(/^Missing:/)).toBeNull();
    });

    it("treats an empty stored expression as no condition yet", async () => {
      const { onOutput } = await renderBuilder({ value: {} as FieldExpression });
      expect(screen.queryByText("This uses advanced logic — edit in full editor.")).toBeNull();
      expect(screen.getByLabelText("Value")).toBeInTheDocument();
      expect(onOutput).not.toHaveBeenCalled();
    });
  });

  describe("missing values", () => {
    it("names the missing value in danger text and reports the sentence as not valid", async () => {
      const onValidityChange = vi.fn();
      await renderBuilder({
        value: { field: "lantern_oil", op: "<=", value: 2, AND: { field: "gone_value", op: "==", value: true } },
        onValidityChange,
      });

      const missing = screen.getByText("Missing: Gone value");
      expect(missing).toHaveClass("text-danger");
      await waitFor(() => expect(onValidityChange).toHaveBeenLastCalledWith(false), WAIT);
    });

    it("sends a text value to the full editor and never calls it missing", async () => {
      const { onOutput } = await renderBuilder(
        { value: { field: "mood", op: "==", value: "calm" } },
        {
          scenario: buildScenarioFixture({
            mode: "master",
            state_schema: { ...STATE_SCHEMA, mood: { type: "string" as const, label: "Mood", initial: "calm" } },
          }),
        },
      );

      expect(await screen.findByText("This uses advanced logic — edit in full editor.")).toBeInTheDocument();
      expect(screen.queryByText(/^Missing:/)).toBeNull();
      expect(onOutput).not.toHaveBeenCalled();
    });

    it("sends a reserved value such as the current place to the full editor", async () => {
      await renderBuilder({ value: { field: "current_location_id", op: "==", value: "docks" } });
      expect(await screen.findByText("This uses advanced logic — edit in full editor.")).toBeInTheDocument();
      expect(screen.queryByText(/^Missing:/)).toBeNull();
    });

    it("sends a card text attribute to the full editor", async () => {
      const guard = buildEntityFixture({
        entity_id: "guard-1",
        canonical_name: "Guard",
        attributes_schema: { mood: { type: "string", label: "Mood" } },
      });
      await renderBuilder({ value: { field: "guard-1.mood", op: "==", value: "calm" } }, { entities: [guard] });
      expect(await screen.findByText("This uses advanced logic — edit in full editor.")).toBeInTheDocument();
      expect(screen.queryByText(/^Missing:/)).toBeNull();
    });

    it("reports a sentence whose values all exist as valid", async () => {
      const onValidityChange = vi.fn();
      await renderBuilder({ value: { field: "lantern_oil", op: "<=", value: 2 }, onValidityChange });
      await waitFor(() => expect(onValidityChange).toHaveBeenLastCalledWith(true), WAIT);
    });

    it("does not emit a sentence that still names a missing value", async () => {
      const { user, onOutput } = await renderBuilder({
        value: { field: "gone_value", op: "==", value: true },
      });
      await user.click(screen.getByRole("button", { name: "+ Add another" }));
      expect(onOutput).not.toHaveBeenCalled();
    });
  });
});
