import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { disableEditGuard, enableEditGuard } from "../../lib/editGuard";
import { useStudioStore } from "../../stores/studio.store";
import { useEntities } from "../useEntities";

const SCENARIO_ID = "scenario-1";
const STAMPS = ["2026-10-27T10:00:00Z", "2026-10-27T10:00:05Z", "2026-10-27T10:00:09Z"];

const entityFixture = (stamp: string) => ({
  entity_id: "entity-1",
  scenario_id: SCENARIO_ID,
  entity_type: "character",
  canonical_name: "Mara",
  aliases: ["Mara"],
  description: null,
  obtainable: null,
  attributes_schema: {},
  narrator_instruction: null,
  lore_document: { blocks: [] },
  scenario_content_edited_at: stamp,
});

const buildWrapper = (queryClient: QueryClient): React.FC<{ children: React.ReactNode }> =>
  function Wrapper({ children }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };

describe("useEntities with the two-window guard on", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    queryClient.setQueryData(["scenario", SCENARIO_ID], { content_edited_at: STAMPS[0] });
    enableEditGuard(SCENARIO_ID);
    useStudioStore.getState().setHasEditConflict(false);
    server.use(
      http.get(`*/v1/scenarios/${SCENARIO_ID}/entities`, () =>
        HttpResponse.json({ items: [] }),
      ),
    );
  });

  afterEach(() => disableEditGuard(SCENARIO_ID));

  it("sends the cached stamp and chains the stamp from each response", async () => {
    const bodies: Array<Record<string, unknown>> = [];
    server.use(
      http.patch(`*/v1/scenarios/${SCENARIO_ID}/entities/entity-1`, async ({ request }) => {
        bodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json(entityFixture(STAMPS[bodies.length]));
      }),
    );
    const { result } = renderHook(() => useEntities(SCENARIO_ID), {
      wrapper: buildWrapper(queryClient),
    });

    await act(async () => {
      await Promise.all([
        result.current.updateEntityAsync({ entityId: "entity-1", payload: { canonical_name: "A" } }),
        result.current.updateEntityAsync({ entityId: "entity-1", payload: { canonical_name: "B" } }),
      ]);
    });

    expect(bodies.map((body) => body.expected_content_edited_at)).toEqual([STAMPS[0], STAMPS[1]]);
  });

  it("sends the stamp on delete and refetches the scenario before the next write", async () => {
    const deleteStamps: Array<string | null> = [];
    const patchStamps: Array<unknown> = [];
    server.use(
      http.delete(`*/v1/scenarios/${SCENARIO_ID}/entities/entity-1`, ({ request }) => {
        deleteStamps.push(new URL(request.url).searchParams.get("expected_content_edited_at"));
        return new HttpResponse(null, { status: 204 });
      }),
      http.get(`*/v1/scenarios/${SCENARIO_ID}`, () =>
        HttpResponse.json({ scenario_id: SCENARIO_ID, content_edited_at: STAMPS[2] }),
      ),
      http.patch(`*/v1/scenarios/${SCENARIO_ID}/entities/entity-1`, async ({ request }) => {
        patchStamps.push(((await request.json()) as Record<string, unknown>).expected_content_edited_at);
        return HttpResponse.json(entityFixture(STAMPS[2]));
      }),
    );
    const { result } = renderHook(() => useEntities(SCENARIO_ID), {
      wrapper: buildWrapper(queryClient),
    });

    await act(async () => {
      await result.current.deleteEntityAsync("entity-1");
      await result.current.updateEntityAsync({ entityId: "entity-1", payload: {} });
    });

    expect(deleteStamps).toEqual([STAMPS[0]]);
    expect(patchStamps).toEqual([STAMPS[2]]);
  });

  it("raises the edit-conflict flag on a scenario_edit_conflict 409", async () => {
    server.use(
      http.patch(`*/v1/scenarios/${SCENARIO_ID}/entities/entity-1`, () =>
        HttpResponse.json(
          { detail: "changed", code: "scenario_edit_conflict" },
          { status: 409 },
        ),
      ),
    );
    const { result } = renderHook(() => useEntities(SCENARIO_ID), {
      wrapper: buildWrapper(queryClient),
    });

    await act(async () => {
      await result.current
        .updateEntityAsync({ entityId: "entity-1", payload: {} })
        .catch(() => undefined);
    });

    await waitFor(() => expect(useStudioStore.getState().hasEditConflict).toBe(true));
  });
});
