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

const intervalWidth = (range: StrengthInterval): number => range.maximum - range.minimum;

export function withLiveEnemyEstimate(
  report: ExchangeReport,
  liveStrength: StrengthInterval | undefined,
): ExchangeReport {
  if (!liveStrength) return report;
  if (intervalWidth(liveStrength) > intervalWidth(report.opponent_strength)) return report;
  return { ...report, opponent_strength: liveStrength };
}

export function withLiveEnemyEstimateOnLatest(
  reports: ExchangeReport[],
  liveStrength: StrengthInterval | undefined,
): ExchangeReport[] {
  const latest = findLatestReport(reports);
  if (!latest) return reports;
  return reports.map((report) =>
    report === latest ? withLiveEnemyEstimate(report, liveStrength) : report,
  );
}

const TROOP_LABELS: Record<string, string> = {
  infantry: "Infantry",
  archers_siege: "Archers & siege",
  cavalry: "Cavalry",
};

export const formatTroopLabel = (troopType: string): string =>
  TROOP_LABELS[troopType] ?? troopType.replace(/_/g, " ");

export function describeLossesByType(losses: Record<string, number>): string {
  const parts = Object.entries(losses)
    .filter(([, count]) => count > 0)
    .map(([troopType, count]) => `${formatTroopLabel(troopType)} ${count.toLocaleString()}`);
  return parts.length > 0 ? parts.join(", ") : "none";
}

const formatRange = (range: StrengthInterval): string =>
  range.exact !== undefined
    ? range.exact.toLocaleString()
    : `${range.minimum.toLocaleString()}–${range.maximum.toLocaleString()}`;

export function describeEnemyEstimate(
  report: ExchangeReport,
  previous: ExchangeReport | undefined,
): string {
  const now = formatRange(report.opponent_strength);
  if (!previous) return `Enemy host estimated at ${now}`;
  return `Enemy host estimated at ${now} (was ${formatRange(previous.opponent_strength)})`;
}
