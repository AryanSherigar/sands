import type { FC } from "react";
import { SovereignBadge } from "./SovereignBadge";
import { TopCanopyControls } from "./TopCanopyControls";
import type { StrategyTopCanopyProps } from "./StrategyTopCanopy.types";

export const StrategyTopCanopy: FC<StrategyTopCanopyProps> = ({
  world,
  activeMapMode = "political",
  onSelectMapMode,
  activeCrisesCount = 0,
  onToggleSituations,
}) => (
  <header className="fixed top-4 inset-x-4 z-40 flex items-center justify-between pointer-events-none">
    <SovereignBadge name={world?.ruler?.name} />
    <div className="flex items-center gap-2 pointer-events-auto">
      {activeCrisesCount > 0 && (
        <button
          type="button"
          onClick={onToggleSituations}
          className="flex items-center gap-1.5 px-3 py-1 bg-tertiary-fixed text-on-tertiary-fixed-variant rounded-full hover:brightness-95 transition-all text-xs font-bold"
        >
          <span className="w-2 h-2 rounded-full bg-tertiary animate-pulse" />
          <span>
            {activeCrisesCount} Active {activeCrisesCount === 1 ? "Crisis" : "Crises"}
          </span>
        </button>
      )}
      <TopCanopyControls
        world={world}
        activeMapMode={activeMapMode}
        onSelectMapMode={onSelectMapMode}
      />
    </div>
  </header>
);
