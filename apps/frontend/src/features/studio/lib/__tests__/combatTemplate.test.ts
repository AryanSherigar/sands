import { describe, expect, it } from "vitest";
import { buildCombatTemplate, readCombatDraft } from "../combatTemplate";
const actor = { max_health: "20", health: "15", attack: "6", armor: "2", speed: "4", accuracy: "75", luck: "10" };
const draft = { title: "Road encounter", trigger: "ready", player: actor, opponent: actor, recoveryHealth: "4", recoveryLocationId: "", playerAttackTag: "", opponentRequiredTag: "", outcomeKind: "recover" as const, endingId: "" };
describe("creator combat template", () => {
    it("uses creator values and preserves unrelated schema", () => {
        const result = buildCombatTemplate(draft, { ready: { type: "boolean", initial: false } }, "test");
        expect(result.encounter.start_condition).toEqual({ field: "ready", op: "==", value: true });
        expect(result.encounter.player).toMatchObject({ health: 15, attack: 6, luck: 10 });
        expect(result.stateSchema.ready.initial).toBe(false);
        expect(result.stateSchema.player.fields?.health.initial).toBe(15);
    });
    it("rejects invalid or conflicting health instead of overwriting creator values", () => {
        expect(() => buildCombatTemplate({ ...draft, recoveryHealth: "0" }, {}, "test")).toThrow();
        expect(() => buildCombatTemplate(draft, { player: { type: "object", fields: { health: { type: "number", initial: 3 } } } }, "test")).toThrow();
    });
    it("supports authored attack tags and explicit defeat endings", () => {
        const result = buildCombatTemplate({ ...draft, playerAttackTag: "silver", opponentRequiredTag: "silver", outcomeKind: "end", endingId: "ending-1" }, {}, "test");
        expect(result.encounter.player).toMatchObject({ attack_tags: ["silver"] });
        expect(result.encounter.opponent).toMatchObject({ required_attack_tag: "silver" });
        expect(result.encounter.outcomes).toEqual([{ id: "recovery", kind: "recover", health: 4 }, { id: "defeat", kind: "end", ending_id: "ending-1" }]);
        expect(readCombatDraft(result.encounter)).toMatchObject({ outcomeKind: "end", recoveryHealth: "4", endingId: "ending-1", playerAttackTag: "silver" });
        expect(() => buildCombatTemplate({ ...draft, opponentRequiredTag: "silver" }, {}, "test")).toThrow();
    });
});
