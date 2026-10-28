import { TurnLogResponse } from "../../api/turns.api";

export interface SpectatorTurnRowProps {
  turn: TurnLogResponse;
  fontClass: string;
}

export function SpectatorTurnRow({ turn, fontClass }: SpectatorTurnRowProps) {
  return (
    <div className="space-y-2">
      <p className="font-serif italic text-stone-300 text-sm bg-stone-900/40 p-3 rounded-lg">
        "{turn.action_text}"
      </p>
      {turn.narration_text && (
        <p
          className={`${fontClass} text-stone-100 text-[15px] leading-relaxed`}
        >
          {turn.narration_text}
        </p>
      )}
    </div>
  );
}
