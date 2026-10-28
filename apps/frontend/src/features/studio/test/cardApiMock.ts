import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import type { EntityResponse } from "../types/entity.types";
import type { FactResponse } from "../types/fact.types";

export const CARD_TEST_SCENARIO_ID = "scenario-1";

export interface CardApiState {
  entities: EntityResponse[];
  facts: FactResponse[];
  entityUpdates: Array<{ entityId: string; body: Record<string, unknown> }>;
  factCreates: Array<Record<string, unknown>>;
  factUpdates: Array<{ factId: string; body: Record<string, unknown> }>;
  deletedEntityIds: string[];
  deletedFactIds: string[];
}

export const buildEntityFixture = (
  overrides: Partial<EntityResponse> & Pick<EntityResponse, "entity_id" | "canonical_name">,
): EntityResponse => ({
  scenario_id: CARD_TEST_SCENARIO_ID,
  entity_type: "character",
  aliases: [overrides.canonical_name],
  description: null,
  obtainable: null,
  attributes_schema: {},
  narrator_instruction: null,
  lore_document: { blocks: [] },
  ...overrides,
});

export const buildFactFixture = (
  overrides: Partial<FactResponse> &
    Pick<FactResponse, "fact_id" | "subject_entity_id" | "predicate" | "object_entity_id">,
): FactResponse => ({
  scenario_id: CARD_TEST_SCENARIO_ID,
  object_literal: null,
  valid_from: null,
  when_active: null,
  hidden: false,
  superseded_fact_id: null,
  ...overrides,
});

export const installCardApi = (
  initial: Pick<CardApiState, "entities" | "facts">,
): CardApiState => {
  const state: CardApiState = {
    ...initial,
    entityUpdates: [],
    factCreates: [],
    factUpdates: [],
    deletedEntityIds: [],
    deletedFactIds: [],
  };
  const base = `*/v1/scenarios/${CARD_TEST_SCENARIO_ID}`;
  server.use(
    http.get(`${base}/entities`, () => HttpResponse.json({ items: state.entities })),
    http.get(`${base}/facts`, () => HttpResponse.json({ items: state.facts })),
    http.patch(`${base}/entities/:entityId`, async ({ request, params }) => {
      const body = (await request.json()) as Record<string, unknown>;
      const entityId = String(params.entityId);
      state.entityUpdates.push({ entityId, body });
      state.entities = state.entities.map((entity) =>
        entity.entity_id === entityId ? ({ ...entity, ...body } as EntityResponse) : entity,
      );
      return HttpResponse.json(state.entities.find((entity) => entity.entity_id === entityId));
    }),
    http.post(`${base}/entities`, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      const created = buildEntityFixture({
        entity_id: `entity-${state.entities.length + 1}`,
        canonical_name: String(body.canonical_name),
        ...(body as Partial<EntityResponse>),
      });
      state.entities = [...state.entities, created];
      return HttpResponse.json(created, { status: 201 });
    }),
    http.delete(`${base}/entities/:entityId`, ({ params }) => {
      const entityId = String(params.entityId);
      state.deletedEntityIds.push(entityId);
      state.entities = state.entities.filter((entity) => entity.entity_id !== entityId);
      state.facts = state.facts.filter(
        (fact) => fact.subject_entity_id !== entityId && fact.object_entity_id !== entityId,
      );
      return new HttpResponse(null, { status: 204 });
    }),
    http.post(`${base}/facts`, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      state.factCreates.push(body);
      const created = buildFactFixture({
        fact_id: `fact-${state.facts.length + 1}`,
        ...(body as Partial<FactResponse>),
        subject_entity_id: String(body.subject_entity_id),
        predicate: String(body.predicate),
        object_entity_id: body.object_entity_id ? String(body.object_entity_id) : null,
      });
      state.facts = [...state.facts, created];
      return HttpResponse.json(created, { status: 201 });
    }),
    http.patch(`${base}/facts/:factId`, async ({ request, params }) => {
      const body = (await request.json()) as Record<string, unknown>;
      const factId = String(params.factId);
      state.factUpdates.push({ factId, body });
      state.facts = state.facts.map((fact) =>
        fact.fact_id === factId ? ({ ...fact, ...body } as FactResponse) : fact,
      );
      return HttpResponse.json(state.facts.find((fact) => fact.fact_id === factId));
    }),
    http.delete(`${base}/facts/:factId`, ({ params }) => {
      const factId = String(params.factId);
      state.deletedFactIds.push(factId);
      state.facts = state.facts.filter((fact) => fact.fact_id !== factId);
      return new HttpResponse(null, { status: 204 });
    }),
  );
  return state;
};
