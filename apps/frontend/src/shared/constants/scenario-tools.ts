// Keys and `requires` edges must equal apps/core-api/app/tools/registry.py;
// apps/core-api/tests/test_frontend_constants_drift.py parses this file, so keep
// one `key:` / `requires:` pair per tool in this exact shape.
export const TOOL_KEYS = [
  "rule_checks",
  "rule_sheet",
  "status_hud",
  "atmosphere",
  "composure",
] as const;

export type ToolKey = (typeof TOOL_KEYS)[number];

export interface ScenarioToolDefinition {
  key: ToolKey;
  displayName: string;
  summary: string;
  requires: readonly ToolKey[];
}

export const SCENARIO_TOOLS: readonly ScenarioToolDefinition[] = [
  {
    key: "rule_checks",
    displayName: "Rule checks",
    summary: "Timed prompts and recall tests",
    requires: [],
  },
  {
    key: "rule_sheet",
    displayName: "Rules & clipboard",
    summary: "A rule sheet that changes as you play",
    requires: [],
  },
  {
    key: "status_hud",
    displayName: "Status HUD",
    summary: "Clock, meters and tension display",
    requires: [],
  },
  {
    key: "atmosphere",
    displayName: "Atmosphere",
    summary: "Cues, audio and reader effects",
    requires: ["status_hud"],
  },
  {
    key: "composure",
    displayName: "Composure minigame",
    summary: "Rhythm challenges",
    requires: [],
  },
];

export const isToolKey = (value: string): value is ToolKey =>
  (TOOL_KEYS as readonly string[]).includes(value);

export const getEnabledDependents = (
  key: ToolKey,
  enabledTools: readonly string[],
): ToolKey[] =>
  SCENARIO_TOOLS.filter(
    (tool) => enabledTools.includes(tool.key) && tool.requires.includes(key),
  ).map((tool) => tool.key);
