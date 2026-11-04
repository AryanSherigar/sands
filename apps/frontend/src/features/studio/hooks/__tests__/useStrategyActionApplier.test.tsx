import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import { TITLE_MAX_LENGTH } from "../../constants/guideLimits";
import { readStrategyFields } from "../../lib/strategyDocument";
import type { ActionBlock } from "../../types/assistant.types";
import type { StrategyFields } from "../../types/strategyDocument.types";
import { useStrategyActionApplier } from "../useStrategyActionApplier";

const API_URL = "http://localhost:8000";
const SCENARIO_URL = `${API_URL}/v1/scenarios/scenario-1`;

const block = (target: ActionBlock["target"], body: unknown): ActionBlock => ({
  target,
  content: typeof body === "string" ? body : JSON.stringify(body),
});

const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>
);

const setup = (scenarioId: string | null = "scenario-1") => {
  const state = { fields: readStrategyFields({}) };
  const edit = vi.fn((change: (current: StrategyFields) => StrategyFields) => {
    state.fields = change(state.fields);
  });
  const hook = renderHook(
    () => useStrategyActionApplier({ scenarioId, edit, knownRegionIds: new Set(["north"]) }),
    { wrapper },
  );
  return { state, edit, hook };
};

describe("useStrategyActionApplier", () => {
  it("applies a faction and a claim on it in one batch, in order", async () => {
    const { state, hook } = setup();
    const onError = vi.fn();

    let outcomes: boolean[] = [];
    await act(async () => {
      outcomes = await hook.result.current.applyBatch(
        [block("faction", { temp_id: "east", name: "Eastmark" }), block("claim", { faction_id: "east", region_id: "north" })],
        onError,
      );
    });

    expect(outcomes).toEqual([true, true]);
    expect(onError).not.toHaveBeenCalled();
    expect(state.fields.claims).toEqual([{ faction_id: "eastmark", region_id: "north" }]);
  });

  it("reports a rejected block and keeps outcomes aligned with the blocks", async () => {
    const { hook } = setup();
    const onError = vi.fn();
    let savedBody: unknown = null;
    server.use(
      http.patch(SCENARIO_URL, async ({ request }) => {
        savedBody = await request.json();
        return HttpResponse.json({ scenario_id: "scenario-1" });
      }),
    );

    let outcomes: boolean[] = [];
    await act(async () => {
      outcomes = await hook.result.current.applyBatch(
        [block("claim", { faction_id: "ghost", region_id: "north" }), block("title", "A Better Name")],
        onError,
      );
    });

    expect(outcomes).toEqual([false, true]);
    expect(onError).toHaveBeenCalledWith("The claim needs an existing faction and region.");
    expect(savedBody).toEqual({ title: "A Better Name" });
  });

  it("refuses a title that is too long and never calls the API", async () => {
    const { hook } = setup();
    const onError = vi.fn();
    const handleSave = vi.fn(() => HttpResponse.json({ scenario_id: "scenario-1" }));
    server.use(http.patch(SCENARIO_URL, handleSave));

    let outcomes: boolean[] = [];
    await act(async () => {
      outcomes = await hook.result.current.applyBatch([block("title", "x".repeat(TITLE_MAX_LENGTH + 1))], onError);
    });

    expect(outcomes).toEqual([false]);
    expect(handleSave).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledWith(expect.stringContaining(String(TITLE_MAX_LENGTH)));
  });

  it("reports a failed title save", async () => {
    const { hook } = setup();
    const onError = vi.fn();
    server.use(http.patch(SCENARIO_URL, () => HttpResponse.json({ detail: "boom" }, { status: 500 })));

    let outcomes: boolean[] = [];
    await act(async () => {
      outcomes = await hook.result.current.applyBatch([block("title", "New")], onError);
    });

    expect(outcomes).toEqual([false]);
    expect(onError).toHaveBeenCalledWith("Couldn't save the title. Try again.");
  });

  it("does not duplicate a faction when the same batch is applied twice", async () => {
    const { state, hook } = setup();

    await act(async () => {
      await hook.result.current.applyBatch([block("faction", { temp_id: "east", name: "Eastmark" })], vi.fn());
      await hook.result.current.applyBatch([block("faction", { temp_id: "east", name: "Eastmark" })], vi.fn());
    });

    expect(state.fields.factions.filter((item) => item.name === "Eastmark")).toHaveLength(1);
  });
});
