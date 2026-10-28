import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { disableEditGuard, enableEditGuard } from "../../lib/editGuard";
import { useDraftOnFirstWord } from "../useDraftOnFirstWord";
import { useScenarioAutosave } from "../useScenarioAutosave";

const SCENARIO_ID = "scenario-1";
const SAVE_TIMEOUT_MS = 3000;

const scenarioFixture = (overrides: Record<string, unknown> = {}) => ({
  scenario_id: SCENARIO_ID,
  title: "",
  logline: null,
  mode: "newbie",
  visibility: "private",
  world_data: { alwaysRemember: ["Keep it short"] },
  content_edited_at: "2026-10-27T10:00:00Z",
  ...overrides,
});

const buildWrapper = (queryClient: QueryClient): React.FC<{ children: React.ReactNode }> =>
  function Wrapper({ children }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };

const renderAutosave = (initialId: string | null, queryClient = new QueryClient()) => {
  const created: string[] = [];
  const hook = renderHook(
    ({ id }: { id: string | null }) => {
      const draft = useDraftOnFirstWord({ onCreated: (scenario) => created.push(scenario.scenario_id) });
      return useScenarioAutosave(id, draft.createDraft);
    },
    { wrapper: buildWrapper(queryClient), initialProps: { id: initialId } },
  );
  return { ...hook, created, queryClient };
};

describe("useScenarioAutosave", () => {
  afterEach(() => disableEditGuard(SCENARIO_ID));

  it("makes no request for blank input and creates one private newbie draft on the first word", async () => {
    const posts: Array<Record<string, unknown>> = [];
    server.use(
      http.post("*/v1/scenarios", async ({ request }) => {
        posts.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json(scenarioFixture({ logline: "A" }), { status: 201 });
      }),
    );
    const { result, created } = renderAutosave(null);

    act(() => result.current.save({ logline: "  " }));
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(posts).toHaveLength(0);

    act(() => {
      result.current.save({ logline: "A" });
      result.current.save({ logline: "A l" });
    });
    await waitFor(() => expect(created).toEqual([SCENARIO_ID]), { timeout: SAVE_TIMEOUT_MS });
    expect(posts).toHaveLength(1);
    expect(posts[0]).toMatchObject({ mode: "newbie", visibility: "private", logline: "A" });
  });

  it("sends what was typed while the draft was being created as a follow-up save", async () => {
    const patches: Array<Record<string, unknown>> = [];
    server.use(
      http.post("*/v1/scenarios", async () => {
        await new Promise((resolve) => setTimeout(resolve, 30));
        return HttpResponse.json(scenarioFixture({ logline: "A" }), { status: 201 });
      }),
      http.patch(`*/v1/scenarios/${SCENARIO_ID}`, async ({ request }) => {
        patches.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json(scenarioFixture());
      }),
    );
    const { result } = renderAutosave(null);

    act(() => result.current.save({ logline: "A" }));
    act(() => result.current.save({ title: "The Door" }));
    await waitFor(() => expect(patches).toHaveLength(1), { timeout: SAVE_TIMEOUT_MS });
    expect(patches[0]).toEqual({
      title: "The Door",
      expected_content_edited_at: "2026-10-27T10:00:00Z",
    });
  });

  it("merges rapid edits into one debounced save and keeps existing world data keys", async () => {
    const patches: Array<Record<string, unknown>> = [];
    server.use(
      http.patch(`*/v1/scenarios/${SCENARIO_ID}`, async ({ request }) => {
        patches.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json(scenarioFixture());
      }),
    );
    const queryClient = new QueryClient();
    queryClient.setQueryData(["scenario", SCENARIO_ID], scenarioFixture());
    const { result } = renderAutosave(SCENARIO_ID, queryClient);

    act(() => {
      result.current.save({ title: "T" });
      result.current.save({ title: "The Door", worldData: { worldLoreDocument: { blocks: [] } } });
    });
    await waitFor(() => expect(patches).toHaveLength(1), { timeout: SAVE_TIMEOUT_MS });
    expect(patches[0]).toEqual({
      title: "The Door",
      world_data: { alwaysRemember: ["Keep it short"], worldLoreDocument: { blocks: [] } },
    });
  });

  it("reports a failed save and sends it again on retry", async () => {
    let attempts = 0;
    server.use(
      http.patch(`*/v1/scenarios/${SCENARIO_ID}`, () => {
        attempts += 1;
        if (attempts === 1) return HttpResponse.json({ detail: "boom" }, { status: 500 });
        return HttpResponse.json(scenarioFixture());
      }),
    );
    const { result } = renderAutosave(SCENARIO_ID);

    act(() => result.current.save({ title: "The Door" }));
    await waitFor(() => expect(result.current.hasError).toBe(true), { timeout: SAVE_TIMEOUT_MS });

    act(() => result.current.retry());
    await waitFor(() => expect(result.current.hasError).toBe(false), { timeout: SAVE_TIMEOUT_MS });
    expect(attempts).toBe(2);
  });
  it("keeps the failure visible until a later write that carries the failed field succeeds", async () => {
    const patches: Array<Record<string, unknown>> = [];
    server.use(
      http.patch(`*/v1/scenarios/${SCENARIO_ID}`, async ({ request }) => {
        patches.push((await request.json()) as Record<string, unknown>);
        if (patches.length <= 2) return HttpResponse.json({ detail: "boom" }, { status: 500 });
        return HttpResponse.json(scenarioFixture());
      }),
    );
    const { result } = renderAutosave(SCENARIO_ID);

    act(() => result.current.save({ title: "The Door" }));
    await waitFor(() => expect(result.current.hasError).toBe(true), { timeout: SAVE_TIMEOUT_MS });

    act(() => result.current.save({ logline: "A door." }));
    await waitFor(() => expect(patches).toHaveLength(2), { timeout: SAVE_TIMEOUT_MS });
    expect(patches[1]).toMatchObject({ title: "The Door", logline: "A door." });
    await waitFor(() => expect(result.current.hasError).toBe(true));

    act(() => result.current.save({ logline: "A locked door." }));
    await waitFor(() => expect(result.current.hasError).toBe(false), { timeout: SAVE_TIMEOUT_MS });
    expect(patches[2]).toMatchObject({ title: "The Door", logline: "A locked door." });
  });

  it("does not clear an earlier failure when an unrelated write queued before it succeeds", async () => {
    enableEditGuard(SCENARIO_ID);
    let titleAttempts = 0;
    server.use(
      http.patch(`*/v1/scenarios/${SCENARIO_ID}`, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        if (!("title" in body)) return HttpResponse.json(scenarioFixture());
        titleAttempts += 1;
        await new Promise((resolve) => setTimeout(resolve, 100));
        return HttpResponse.json({ detail: "boom" }, { status: 500 });
      }),
    );
    const queryClient = new QueryClient();
    queryClient.setQueryData(["scenario", SCENARIO_ID], scenarioFixture());
    const { result } = renderAutosave(SCENARIO_ID, queryClient);

    let first: Promise<boolean> = Promise.resolve(true);
    let second: Promise<boolean> = Promise.resolve(true);
    act(() => {
      result.current.save({ title: "The Door" });
      first = result.current.flush();
      result.current.save({ logline: "A door." });
      second = result.current.flush();
    });
    await act(async () => {
      await Promise.all([first, second]);
    });

    expect(titleAttempts).toBe(1);
    expect(result.current.hasError).toBe(true);
  });
});
