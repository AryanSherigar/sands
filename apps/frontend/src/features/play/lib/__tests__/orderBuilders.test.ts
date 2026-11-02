import { describe, it, expect } from "vitest";
import {
  buildSetTaxRateOrder,
  buildTakeLoanOrder,
  buildDeclareDefaultOrder,
  buildSetPayOrder,
  buildDeclareWarOrder,
  buildSuePeaceOrder,
  buildCallNegotiationOrder,
  buildSendEnvoyOrder,
  buildAnswerCallOrder,
  buildAnswerDemandOrder,
  buildBesiegeOrder,
} from "../orderBuilders";

describe("buildSetTaxRateOrder", () => {
  it("returns a set_tax_rate order with correct shape", () => {
    expect(buildSetTaxRateOrder("f-1", "high")).toEqual({
      kind: "set_tax_rate",
      faction_id: "f-1",
      tax_rate: "high",
    });
  });
});

describe("buildTakeLoanOrder", () => {
  it("returns a take_loan order with correct amount", () => {
    expect(buildTakeLoanOrder("f-1", 500)).toEqual({
      kind: "take_loan",
      faction_id: "f-1",
      amount: 500,
    });
  });
});

describe("buildDeclareDefaultOrder", () => {
  it("returns a declare_default order", () => {
    expect(buildDeclareDefaultOrder("f-1")).toEqual({
      kind: "declare_default",
      faction_id: "f-1",
    });
  });
});

describe("buildSetPayOrder", () => {
  it("returns a set_pay order with army and pay level", () => {
    expect(buildSetPayOrder("f-1", "a-3", "reduced")).toEqual({
      kind: "set_pay",
      faction_id: "f-1",
      army_id: "a-3",
      pay_level: "reduced",
    });
  });
});

describe("War and Peace Order Builders", () => {
  it("builds a declare war order with ground", () => {
    const order = buildDeclareWarOrder("faction-aldric", "faction-mira", "ground-border");
    expect(order).toEqual({
      kind: "declare_war",
      faction_id: "faction-aldric",
      target_faction_id: "faction-mira",
      ground_id: "ground-border",
    });
  });

  it("builds a declare war order without ground", () => {
    const order = buildDeclareWarOrder("faction-aldric", "faction-mira");
    expect(order).toEqual({
      kind: "declare_war",
      faction_id: "faction-aldric",
      target_faction_id: "faction-mira",
      ground_id: null,
    });
  });

  it("builds a sue for peace order", () => {
    const order = buildSuePeaceOrder("faction-aldric", "war-three-crowns");
    expect(order).toEqual({
      kind: "sue_peace",
      faction_id: "faction-aldric",
      war_id: "war-three-crowns",
    });
  });

  it("builds a call negotiation order", () => {
    const order = buildCallNegotiationOrder("faction-aldric", "faction-mira");
    expect(order).toEqual({
      kind: "call_negotiation",
      faction_id: "faction-aldric",
      target_faction_id: "faction-mira",
    });
  });

  it("builds a send envoy order", () => {
    const order = buildSendEnvoyOrder("faction-aldric", "faction-mira");
    expect(order).toEqual({
      kind: "send_envoy",
      faction_id: "faction-aldric",
      target_faction_id: "faction-mira",
    });
  });

  it("builds an answer call order", () => {
    const order = buildAnswerCallOrder("faction-aldric", "call-42", true);
    expect(order).toEqual({
      kind: "answer_call",
      faction_id: "faction-aldric",
      call_id: "call-42",
      is_joining: true,
    });
  });

  it("builds an answer demand order", () => {
    const order = buildAnswerDemandOrder("faction-aldric", "demand-99", "accept");
    expect(order).toEqual({
      kind: "answer_demand",
      faction_id: "faction-aldric",
      demand_id: "demand-99",
      reply: "accept",
    });
  });
});


describe("buildBesiegeOrder", () => {
  it("returns a besiege order aimed at the given region", () => {
    expect(buildBesiegeOrder("f-1", "a-1", "r-9")).toEqual({
      kind: "besiege",
      faction_id: "f-1",
      army_id: "a-1",
      target_region_id: "r-9",
    });
  });
});
