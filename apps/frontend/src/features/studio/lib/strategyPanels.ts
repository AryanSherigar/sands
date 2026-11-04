import type { PublishIssue, StrategyFields } from "../types/strategyDocument.types";

export type StartPanelId = "timeline" | "endings" | "region_economy" | "armies" | "relations" | "claims_grudges" | "rules";

export const START_PANELS: readonly { id: StartPanelId; label: string }[] = [
  { id: "timeline", label: "Timeline" },
  { id: "endings", label: "Victory and endings" },
  { id: "region_economy", label: "Region economy" },
  { id: "armies", label: "Armies" },
  { id: "relations", label: "Relations" },
  { id: "claims_grudges", label: "Claims and grudges" },
  { id: "rules", label: "Rules and simulation" },
];

const CODE_PANELS: Record<string, StartPanelId> = {
  faction_has_no_army: "armies",
  faction_has_no_economy: "region_economy",
  invalid_vassalage: "relations",
};

const PATH_PANELS: readonly [string, StartPanelId][] = [
  ["starting.relations", "relations"],
  ["starting.armies", "armies"],
  ["starting.claims", "claims_grudges"],
  ["starting.grudges", "claims_grudges"],
  ["starting.regions", "region_economy"],
  ["tuning.agents", "rules"],
  ["tuning.treaty", "rules"],
  ["tuning.overtures", "rules"],
  ["tuning.endings", "endings"],
  ["endings", "endings"],
  ["toggles", "rules"],
  ["disabled_builtin_event_ids", "rules"],
  ["tuning", "timeline"],
];

export const panelForIssue = (issue: PublishIssue): StartPanelId | null => {
  const byCode = CODE_PANELS[issue.code];
  if (byCode) return byCode;
  return PATH_PANELS.find(([prefix]) => issue.path.startsWith(prefix))?.[1] ?? null;
};

const pluralize = (count: number, singular: string, plural: string): string =>
  `${count} ${count === 1 ? singular : plural}`;

const summarizeEconomy = (fields: StrategyFields): string => {
  const count = fields.regions.filter((item) => item.owner_id !== null).length;
  return count === 0 ? "Using defaults" : `${pluralize(count, "region", "regions")} with an economy`;
};

const summarizeRelations = (fields: StrategyFields): string => {
  const count = fields.relations.filter((item) => item.status !== "peace").length;
  return count === 0 ? "All at peace" : `${count} not at peace`;
};

const summarizeClaimsGrudges = (fields: StrategyFields): string => {
  if (fields.claims.length + fields.grudges.length === 0) return "Using defaults";
  return `${pluralize(fields.claims.length, "claim", "claims")}, ${pluralize(fields.grudges.length, "grudge", "grudges")}`;
};

const summarizeEndings = (fields: StrategyFields): string => {
  if (fields.is_using_default_endings) return "Default victory rules";
  if (fields.endings.length === 0) return "No custom endings";
  return pluralize(fields.endings.length, "custom ending", "custom endings");
};

export const summarizePanel = (panelId: StartPanelId, fields: StrategyFields): string => {
  const { timing } = fields;
  const summaries: Record<StartPanelId, () => string> = {
    timeline: () => `${timing.start_year}-${String(timing.start_month).padStart(2, "0")} to ${timing.end_year}`,
    endings: () => summarizeEndings(fields),
    region_economy: () => summarizeEconomy(fields),
    armies: () => (fields.armies.length === 0 ? "No armies" : pluralize(fields.armies.length, "army", "armies")),
    relations: () => summarizeRelations(fields),
    claims_grudges: () => summarizeClaimsGrudges(fields),
    rules: () => `${fields.orders_per_turn} orders/turn`,
  };
  return summaries[panelId]();
};
