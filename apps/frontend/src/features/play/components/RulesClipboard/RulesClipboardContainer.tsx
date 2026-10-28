import { recordUiUsed } from "@/shared/lib/alpha-session-stats";
import { useEffect, useState } from "react";
import { RulesClipboard } from "@/shared/components/rules-clipboard/RulesClipboard";
import { prefersReducedMotion } from "@/shared/lib/prefersReducedMotion";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import type { RuleSheetItem } from "@/shared/types/rule-sheet.types";
import { loadNarrationFont } from "@/shared/lib/font-loader";
import { usePlayStore } from "../../stores/play.store";
import { useHasRulesPanel } from "../../hooks/useHasRulesPanel";

const TYPED_HAND_FONT_ID = "special-elite";
const NO_RULES: RuleSheetItem[] = [];
const NO_DUTIES: string[] = [];

/**
 * The rules clipboard for a scenario that switched on the Rules & clipboard
 * tool. Renders nothing when the tool is off or no rule has been revealed yet,
 * so it can be mounted unconditionally. On narrow screens it collapses to a
 * toggle that opens it as a drawer.
 */
export function RulesClipboardContainer() {
  const rules = usePlayStore((s) => s.playthrough?.rule_sheet ?? NO_RULES);
  const duties = usePlayStore((s) => s.playthrough?.duties ?? NO_DUTIES);
  const reduceSensoryEffects = useReaderPreferencesStore(
    (s) => s.reduceSensoryEffects,
  );
  const isPanelHidden = usePlayStore((s) => s.is_rules_panel_hidden);
  const setRulesPanelHidden = usePlayStore((s) => s.setRulesPanelHidden);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const hasRulesPanel = useHasRulesPanel();

  useEffect(() => {
    if (hasRulesPanel) loadNarrationFont(TYPED_HAND_FONT_ID);
  }, [hasRulesPanel]);

  if (!hasRulesPanel) return null;

  const isMotionReduced = reduceSensoryEffects || prefersReducedMotion();
  const handleToggleDrawer = (): void => {
    if (!isDrawerOpen) recordUiUsed("rule_sheet");
    setIsDrawerOpen((isOpen) => !isOpen);
    setRulesPanelHidden(false);
  };
  const handleHidePanel = (): void => setRulesPanelHidden(true);

  return (
    <>
      <button
        type="button"
        onClick={handleToggleDrawer}
        aria-expanded={isDrawerOpen}
        aria-controls="rules-clipboard-panel"
        className={`absolute right-3 top-3 z-20 rounded-lg border border-border-subtle bg-surface-raised px-2.5 py-1.5 font-mono text-xs text-content ${isPanelHidden ? "" : "lg:hidden"}`}
      >
        Rules ({rules.length})
      </button>
      <div
        id="rules-clipboard-panel"
        className={`${isDrawerOpen ? "absolute inset-y-0 right-0 z-30 flex shadow-float" : "hidden"} ${isPanelHidden ? "lg:hidden" : "lg:static lg:flex"}`}
      >
        <div className="relative">
          <button
            type="button"
            onClick={handleHidePanel}
            className="absolute right-3 top-3 hidden cursor-pointer font-mono text-xs text-[#2c2217]/70 hover:text-[#2c2217] lg:block"
          >
            Hide
          </button>
          <RulesClipboard
            rules={rules}
            duties={duties}
            isMotionReduced={isMotionReduced}
          />
        </div>
      </div>
    </>
  );
}
