import type { RuleSheetItem } from "@/shared/types/rule-sheet.types";

// True when `next` lists a rule the clipboard did not show before: a rule being
// revealed, as opposed to an existing one changing status.
export function hasNewlyRevealedRule(
  previous: RuleSheetItem[],
  next: RuleSheetItem[] | undefined,
): boolean {
  if (!next) return false;
  const known = new Set(previous.map((rule) => rule.key));
  return next.some((rule) => !known.has(rule.key));
}
