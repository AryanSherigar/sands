import type { EstimatedSection } from "../types/turnReport.types";

interface TurnReportGap {
  label: string;
  needs: string;
}

/**
 * Report sections the simulation cannot supply yet. A report lists the ids it
 * still estimates in `estimatedSections`. Mirrored in
 * docs/specs/strategy-turn-report-data-gaps.md.
 */
export const TURN_REPORT_GAPS: Record<EstimatedSection, TurnReportGap> = {
  economy_lines: {
    label: "Economy ledger",
    needs: "Only estimated in preview or when GET /turns/{turn}/report fails.",
  },
  casualties: {
    label: "Total casualties",
    needs: "Only estimated in preview or when the report fetch fails.",
  },
  battle_results: {
    label: "Battle results",
    needs: "Only estimated in preview or when the report fetch fails.",
  },
  event_dispatches: {
    label: "Event dispatches",
    needs: "Only estimated in preview or when the report fetch fails.",
  },
  stability_delta: {
    label: "Stability change",
    needs:
      "The engine never changes faction stability and emits no stability event; add an internal-phase stability rule and event.",
  },
  war_score: {
    label: "War score per battle",
    needs: "No war score exists in the simulation; add the field and its rules.",
  },
  rival_casualties: {
    label: "Enemy losses",
    needs:
      "Receipts hide the opponent's losses from the observer; expose them (or an interval) in the report.",
  },
  tactical_round_text: {
    label: "Tactical round narration",
    needs: "Receipts carry numbers only; add per-exchange descriptions or text keys.",
  },
  diplomacy_dispatches: {
    label: "Rival relation changes",
    needs:
      "The diplomacy phase is a no-op and emits no events; add diplomacy rules and events.",
  },
  victory_margin: {
    label: "Decisive versus marginal victory",
    needs:
      "BattleOutcome has no margin; victory by surrender maps to decisive, other victories to marginal.",
  },
};

export const ALL_ESTIMATED_SECTIONS = Object.keys(TURN_REPORT_GAPS) as EstimatedSection[];
