import { useEffect } from "react";
import { TurnLogResponse } from "../../api/turns.api";
import { resolveNarrationFont } from "@/shared/constants/narration-fonts";
import { loadNarrationFont } from "@/shared/lib/font-loader";
import { SpectatorHeader } from "./SpectatorHeader";
import { SpectatorTurnRow } from "./SpectatorTurnRow";

export interface SpectatorViewProps {
  scenarioTitle: string;
  turns: TurnLogResponse[];
  streamingText: string;
  streamingImageUrl?: string | null;
  isLive: boolean;
  narrationFont?: string | null;
}

export function SpectatorView({
  scenarioTitle,
  turns,
  streamingText,
  streamingImageUrl,
  isLive,
  narrationFont,
}: SpectatorViewProps) {
  const activeFont = resolveNarrationFont(narrationFont);

  useEffect(() => {
    loadNarrationFont(activeFont.id);
  }, [activeFont.id]);

  return (
    <div className="min-h-dvh w-full bg-surface-sunken text-content flex flex-col">
      <SpectatorHeader scenarioTitle={scenarioTitle} isLive={isLive} />

      <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 space-y-6 max-w-3xl mx-auto w-full">
        {turns.length === 0 && !streamingText && (
          <p className="text-stone-500 italic text-sm text-center py-12">
            No turns recorded yet.
          </p>
        )}

        {turns.map((turn) => (
          <SpectatorTurnRow
            key={turn.turn_id}
            turn={turn}
            fontClass={activeFont.fontClass}
          />
        ))}

        {streamingImageUrl && (
          <img
            src={streamingImageUrl}
            alt="Scene depiction"
            className="w-full rounded-lg border border-stone-800/60"
          />
        )}

        {streamingText && (
          <p
            className={`${activeFont.fontClass} text-stone-100 text-[15px] leading-relaxed`}
          >
            {streamingText}
            <span className="inline-block w-2 h-4 ml-1 bg-amber-400 animate-pulse align-middle" />
          </p>
        )}
      </div>
    </div>
  );
}
