import type {
  BattleView,
  ExchangeReport,
  StrengthInterval,
} from "../components/StrategyWarCouncil/StrategyWarCouncil.types";

export interface BattleAftermathSummary {
  outcome: string;
  totalOwnLosses: number;
  enemyStrengthRemaining: StrengthInterval | null;
}

const sumValues = (counts: Record<string, number>): number =>
  Object.values(counts).reduce((total, count) => total + count, 0);

export function findLatestReport(reports: ExchangeReport[]): ExchangeReport | null {
  if (reports.length === 0) return null;
  return reports.reduce((latest, report) =>
    report.total_exchange > latest.total_exchange ? report : latest,
  );
}

export function sumOwnLosses(reports: ExchangeReport[]): number {
  return reports.reduce((total, report) => total + sumValues(report.own_losses), 0);
}

export function buildAftermathSummary(
  battle: BattleView,
  reports: ExchangeReport[],
): BattleAftermathSummary | null {
  if (battle.status !== "resolved") return null;
  const latest = findLatestReport(reports);
  return {
    outcome: battle.outcome ?? "mutual_disengagement",
    totalOwnLosses: sumOwnLosses(reports),
    enemyStrengthRemaining: latest?.opponent_strength ?? null,
  };
}
