import { usePlayStore } from "../stores/play.store";

const RULE_SHEET_TOOL_KEY = "rule_sheet";

export function useHasRulesPanel(): boolean {
  return usePlayStore(
    (s) =>
      (s.playthrough?.enabled_tools?.includes(RULE_SHEET_TOOL_KEY) ?? false) &&
      (s.playthrough?.rule_sheet?.length ?? 0) > 0,
  );
}
