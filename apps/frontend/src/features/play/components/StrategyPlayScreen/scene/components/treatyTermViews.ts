import type { ConditionClause, TreatyTerm } from "../../../../types/scene.types";
import type { TreatyTermView } from "./TreatyTermCard.types";

const FOREVER_TEXT = "for as long as both realms stand";

const lengthText = (turns: number, currentTurn: number): string =>
  turns > 0 ? `${turns} turns (ending turn ${currentTurn + turns})` : FOREVER_TEXT;

const PROMISE_TEXT: Record<string, (promisor: string, other: string, subject: string) => string> = {
  never_attack_faction: (promisor, other) => `${promisor} swears never to attack ${other}`,
  never_ally_with: (promisor, _other, subject) => `${promisor} swears never to ally with ${subject}`,
  spare_prisoners: (promisor, other) => `${promisor} swears to spare the prisoners of ${other}`,
};

const CONDITION_TEXT: Record<ConditionClause["template"], (faction: string, value: number) => string> = {
  treasury_below: (faction, value) => `${faction}'s treasury falls below ${value}`,
  treasury_above: (faction, value) => `${faction}'s treasury rises above ${value}`,
  stability_below: (faction, value) => `${faction}'s stability falls below ${value}`,
  war_exhaustion_above: (faction, value) => `${faction}'s war exhaustion rises above ${value}`,
  region_count_below: (faction, value) => `${faction} holds fewer than ${value} regions`,
  region_count_above: (faction, value) => `${faction} holds more than ${value} regions`,
  turn_after: (_faction, value) => `turn ${value} has passed`,
};

const describeCondition = (when: ConditionClause): string =>
  CONDITION_TEXT[when.template](when.faction_id, when.value);

const kindLabel = (kind: string): string =>
  kind
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");

export const describeTreatyTerm = (term: TreatyTerm, currentTurn: number): TreatyTermView => {
  switch (term.kind) {
    case "trade_deal":
      return {
        title: "Trade Deal",
        badge: "Trade",
        icon: "storefront",
        tone: "amber",
        detail: `Both realms prosper from open trade between ${term.faction_a} and ${term.faction_b} for ${lengthText(term.duration_turns, currentTurn)}.`,
      };
    case "military_access":
      return {
        title: "Military Access",
        badge: "Passage",
        icon: "route",
        tone: "sky",
        detail: `${term.grantee_id} may march through ${term.grantor_id}'s land for ${lengthText(term.duration_turns, currentTurn)}.`,
      };
    case "sworn_promise": {
      const describe = PROMISE_TEXT[term.promise] ?? PROMISE_TEXT.never_attack_faction;
      const sentence = describe(term.promisor_id, term.beneficiary_id, term.subject_id ?? "a third realm");
      return {
        title: "Sworn Promise",
        badge: "Oath",
        icon: "swords",
        tone: "purple",
        detail: `${sentence} for ${lengthText(term.duration_turns, currentTurn)}.`,
      };
    }
    case "conditional": {
      const inner = describeTreatyTerm(term.inner, currentTurn);
      const lead = term.mode === "gate" ? "Only while" : "Once";
      return {
        ...inner,
        title: `If: ${inner.title}`,
        badge: term.mode === "gate" ? "Gated" : "Pending",
        detail: `${lead} ${describeCondition(term.when)}: ${inner.detail} Lapses after ${term.expires_in_turns} turns.`,
      };
    }
    case "alliance":
      return {
        title: "Alliance",
        badge: term.alliance_type === "offensive" ? "Offensive" : "Defensive",
        icon: "diversity_3",
        tone: "green",
        detail: `${term.faction_a} and ${term.faction_b} stand together ${term.duration_turns > 0 ? `for ${lengthText(term.duration_turns, currentTurn)}` : FOREVER_TEXT}.`,
      };
    case "vassal":
      return {
        title: "Vassalage",
        badge: "Vassal",
        icon: "account_balance",
        tone: "rose",
        detail: `${term.vassal_id} serves ${term.overlord_id}, paying ${term.tribute_share_percent}% of income ${term.duration_turns > 0 ? `for ${lengthText(term.duration_turns, currentTurn)}` : FOREVER_TEXT}.`,
      };
    default:
      return {
        title: kindLabel(term.kind),
        badge: "Clause",
        icon: "description",
        tone: "green",
        detail: "A clause of this treaty.",
      };
  }
};
