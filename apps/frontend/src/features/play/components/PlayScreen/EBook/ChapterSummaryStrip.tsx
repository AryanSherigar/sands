import { StatChange } from "../../../types/play.types";
import { ChapterSummaryStripProps } from "./ebook.types";
import { useEBookThemeTokens } from "./ebookTheme";
import { IconBackpack, IconChartBar, IconDroplet, IconSparkles } from "@tabler/icons-react";

function StatChangeIcon({ change }: { change: StatChange }) {
  if (change.delta == null) return <IconChartBar size={14} aria-hidden="true" />;
  if (change.delta < 0) return <IconDroplet size={14} aria-hidden="true" />;
  return <IconSparkles size={14} aria-hidden="true" />;
}

function statChangeValue(change: StatChange): string {
  if (change.delta != null) {
    return change.delta > 0 ? `+${change.delta}` : `${change.delta}`;
  }
  return change.after != null ? `${change.after}` : "";
}

export function ChapterSummaryStrip({ delta }: ChapterSummaryStripProps) {
  const tokens = useEBookThemeTokens();
  const hasContent =
    delta.stat_changes.length > 0 || delta.inventory_changes.length > 0;

  if (!hasContent) return null;

  return (
    <div
      className={`my-4 rounded-xl border px-4 py-3 font-mono text-sm space-y-1.5 ${tokens.cardBg} ${tokens.mutedText}`}
    >
      {delta.stat_changes.map((change) => (
        <div key={change.path} className="flex items-center justify-between">
          <span>
            <StatChangeIcon change={change} /> {change.label}
          </span>
          <span>{statChangeValue(change)}</span>
        </div>
      ))}
      {delta.inventory_changes.map((change) => (
        <div
          key={change.path + change.entity_id}
          className="flex items-center gap-2"
        >
          <IconBackpack size={14} aria-hidden="true" />
          <span>+{change.entity_display_name}</span>
        </div>
      ))}
    </div>
  );
}
