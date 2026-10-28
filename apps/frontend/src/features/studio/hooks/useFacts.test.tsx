import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import { useFacts } from "./useFacts";

const SCENARIO_ID = "scenario-1";

const factFixture = {
  fact_id: "fact-1",
  scenario_id: SCENARIO_ID,
  subject_entity_id: "entity-1",
  predicate: "lives in",
  object_entity_id: "entity-2",
  object_literal: null,
  valid_from: null,
  when_active: null,
  hidden: false,
  superseded_fact_id: null,
};

describe("useFacts", () => {
  it("lists every link of the story", async () => {
    server.use(
      http.get("*/v1/scenarios/scenario-1/facts", () =>
        HttpResponse.json({ items: [factFixture] }),
      ),
    );
    const { result } = renderHook(() => useFacts(SCENARIO_ID), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => expect(result.current.facts).toHaveLength(1));
    expect(result.current.facts[0].predicate).toBe("lives in");
  });

  it("creates a hidden link and resolves with the saved row", async () => {
    let body: Record<string, unknown> = {};
    server.use(
      http.get("*/v1/scenarios/scenario-1/facts", () =>
        HttpResponse.json({ items: [] }),
      ),
      http.post("*/v1/scenarios/scenario-1/facts", async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ ...factFixture, hidden: true }, { status: 201 });
      }),
    );
    const { result } = renderHook(() => useFacts(SCENARIO_ID), {
      wrapper: createQueryWrapper(),
    });

    let saved: { hidden: boolean } | undefined;
    await act(async () => {
      saved = await result.current.createFactAsync({
        subject_entity_id: "entity-1",
        predicate: "lives in",
        object_entity_id: "entity-2",
        hidden: true,
      });
    });

    expect(saved?.hidden).toBe(true);
    expect(body).toMatchObject({ hidden: true });
  });
});
