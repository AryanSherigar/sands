import { describe, it, expect } from "vitest";
import { describeOrder } from "../orderSummary";
import type {
  DeclareDefaultOrder,
  QueuedOrderView,
  SetPayOrder,
  SetTaxRateOrder,
  TakeLoanOrder,
} from "../../types/simulation.types";

describe("describeOrder", () => {
  it("describes set_pay order", () => {
    const order: SetPayOrder = {
      kind: "set_pay",
      faction_id: "f-1",
      army_id: "a-1",
      pay_level: "reduced",
    };
    expect(describeOrder({ order } as QueuedOrderView)).toBe("Set pay to reduced");
    expect(describeOrder(order)).toBe("Set pay to reduced");
  });

  it("describes a besiege order with the region name", () => {
    const order = {
      kind: "besiege" as const,
      faction_id: "f-1",
      army_id: "a-1",
      target_region_id: "r-9",
    };
    expect(describeOrder(order, { "r-9": "Carrow Vale" })).toBe("Besiege Carrow Vale");
  });

  it("describes declare_default order", () => {
    const order: DeclareDefaultOrder = {
      kind: "declare_default",
      faction_id: "f-1",
    };
    expect(describeOrder({ order } as QueuedOrderView)).toBe("Declare sovereign default");
    expect(describeOrder(order)).toBe("Declare sovereign default");
  });

  it("describes set_tax_rate order", () => {
    const order: SetTaxRateOrder = {
      kind: "set_tax_rate",
      faction_id: "f-1",
      tax_rate: "high",
    };
    expect(describeOrder(order)).toBe("Set taxes to high");
  });

  it("describes take_loan order", () => {
    const order: TakeLoanOrder = {
      kind: "take_loan",
      faction_id: "f-1",
      amount: 500,
    };
    expect(describeOrder(order)).toBe("Take loan of 500g");
  });

  it("formats war and peace orders correctly", () => {
    const factionNames = { "faction-mira": "Dunmere" };
    expect(
      describeOrder(
        { kind: "declare_war", faction_id: "player", target_faction_id: "faction-mira" },
        {},
        factionNames,
      ),
    ).toBe("Declare war on Dunmere");

    expect(
      describeOrder({ kind: "sue_peace", faction_id: "player", war_id: "war-10" }),
    ).toBe("Sue for peace (War #war-10)");

    expect(
      describeOrder(
        { kind: "call_negotiation", faction_id: "player", target_faction_id: "faction-mira" },
        {},
        factionNames,
      ),
    ).toBe("Summon talks with Dunmere");

    expect(
      describeOrder(
        { kind: "send_envoy", faction_id: "player", target_faction_id: "faction-mira" },
        {},
        factionNames,
      ),
    ).toBe("Dispatch envoy to Dunmere");

    expect(
      describeOrder({ kind: "answer_call", faction_id: "player", call_id: "c-1", is_joining: true }),
    ).toBe("Honour war call");

    expect(
      describeOrder({ kind: "answer_call", faction_id: "player", call_id: "c-1", is_joining: false }),
    ).toBe("Refuse war call");

    expect(
      describeOrder({ kind: "answer_demand", faction_id: "player", demand_id: "d-1", reply: "accept" }),
    ).toBe("Answer demand: accept");
  });
});
