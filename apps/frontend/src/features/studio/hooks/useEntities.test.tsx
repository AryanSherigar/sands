import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import { useEntities } from "./useEntities";

const SCENARIO_ID = "scenario-1";
const STAMP = "2026-10-27T10:00:00Z";

const entityFixture = {
  entity_id: "entity-1",
  scenario_id: SCENARIO_ID,
  entity_type: "character",
  canonical_name: "Mara",
  aliases: ["Mara"],
  description: "The keeper.",
  obtainable: null,
  attributes_schema: {},
  narrator_instruction: null,
  lore_document: { blocks: [{ kind: "text", text: "The keeper." }] },
  scenario_content_edited_at: STAMP,
};

describe("useEntities", () => {
  it("lists entities with their lore document", async () => {
    server.use(
      http.get("*/v1/scenarios/scenario-1/entities", () =>
        HttpResponse.json({ items: [entityFixture] }),
      ),
    );
    const { result } = renderHook(() => useEntities(SCENARIO_ID), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => expect(result.current.entities).toHaveLength(1));
    expect(result.current.entities[0].lore_document?.blocks[0].text).toBe(
      "The keeper.",
    );
  });

  it("does not fetch without a scenario id", () => {
    const { result } = renderHook(() => useEntities(null), {
      wrapper: createQueryWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.entities).toEqual([]);
  });

  it("creates an entity and resolves with the saved row", async () => {
    let body: Record<string, unknown> = {};
    server.use(
      http.get("*/v1/scenarios/scenario-1/entities", () =>
        HttpResponse.json({ items: [] }),
      ),
      http.post("*/v1/scenarios/scenario-1/entities", async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(entityFixture, { status: 201 });
      }),
    );
    const { result } = renderHook(() => useEntities(SCENARIO_ID), {
      wrapper: createQueryWrapper(),
    });

    let saved: { entity_id: string } | undefined;
    await act(async () => {
      saved = await result.current.createEntityAsync({
        entity_type: "location",
        canonical_name: "Lighthouse",
        lore_document: { blocks: [] },
      });
    });

    expect(saved?.entity_id).toBe("entity-1");
    expect(body).toMatchObject({ entity_type: "location" });
  });

  it("sends the expected edit stamp as a query param when deleting", async () => {
    let url = "";
    server.use(
      http.get("*/v1/scenarios/scenario-1/entities", () =>
        HttpResponse.json({ items: [] }),
      ),
      http.delete("*/v1/scenarios/scenario-1/entities/entity-1", ({ request }) => {
        url = request.url;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { result } = renderHook(() => useEntities(SCENARIO_ID), {
      wrapper: createQueryWrapper(),
    });

    await act(async () => {
      await result.current.deleteEntityAsync({
        entityId: "entity-1",
        expectedContentEditedAt: STAMP,
      });
    });

    expect(new URL(url).searchParams.get("expected_content_edited_at")).toBe(
      STAMP,
    );
  });
});
