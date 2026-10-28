import { memo } from "react";
import { IconPlayerPause, IconPlayerPlay } from "@tabler/icons-react";
import { usePlayStore } from "../../../stores/play.store";
import { resolveNarrationFont } from "@/shared/constants/narration-fonts";
import { useVoiceOutputPreference } from "@/shared/hooks/useVoiceOutputPreference";
import { ChapterSummaryStrip } from "./ChapterSummaryStrip";
import { EBookTurnEntryProps } from "./ebook.types";
import { HighlightedParagraph } from "./HighlightedParagraph";
import { NarrationFlag } from "../NarrationFlag/NarrationFlag";

export const EBookTurnEntry = memo(function EBookTurnEntry({
  turn,
  turnIndex,
  isLatest: _isLatest,
  shouldDistort = false,
}: EBookTurnEntryProps) {
  const isSilentContinue = turn.action_text === "Continue the story.";
  const characterName = usePlayStore(
    (s) => s.playthrough?.character_name ?? "Adventurer",
  );
  const playthroughId = usePlayStore((s) => s.playthrough?.playthrough_id ?? "");
  const scenarioFont = usePlayStore((s) => s.playthrough?.narration_font);
  const readerFontOverride = usePlayStore((s) => s.reader_font_override);
  const activeFont = resolveNarrationFont(readerFontOverride ?? scenarioFont);
  const paragraphs = turn.narration_text.split(/\n\s*\n/).filter(Boolean);
  const isPlayingThisTurn = usePlayStore(
    (s) => s.playing_audio_turn_id === turn.id,
  );
  const playTurnAudio = usePlayStore((s) => s.playTurnAudio);
  const stopTurnAudio = usePlayStore((s) => s.stopTurnAudio);
  const { isVoiceOutputEnabled } = useVoiceOutputPreference();

  const handleToggleAudio = (): void => {
    if (isPlayingThisTurn) {
      stopTurnAudio();
    } else if (turn.audio_url) {
      playTurnAudio(turn.id, turn.audio_url);
    }
  };

  return (
    <section className="my-8 pt-6 border-t border-inherit/20 first:border-t-0">
      <header className="flex items-center justify-between font-mono text-xs opacity-60 mb-4 tracking-wider">
        <span className="uppercase">Chapter {turnIndex + 1}</span>
        <span>
          {new Date(turn.created_at).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </header>

      {!isSilentContinue && (
        <aside className="mb-5 pl-4 border-l-2 border-border-strong italic font-serif text-sm opacity-80">
          <span className="font-mono text-xs not-italic opacity-70 mr-1.5 uppercase font-medium">
            {characterName} ({turn.action_mode}):
          </span>
          "{turn.action_text}"
        </aside>
      )}

      <article className="prose-book">
        {paragraphs.map((para: string, idx: number) => (
          <HighlightedParagraph
            key={idx}
            paragraph={para}
            isFirst={idx === 0}
            fontClass={activeFont.fontClass}
            distortion={
              shouldDistort
                ? {
                    playthroughId,
                    turnNumber: turnIndex + 1,
                    paragraphIndex: idx,
                    isComplete: true,
                  }
                : undefined
            }
          />
        ))}
      </article>

      {turn.image_url && (
        <img
          src={turn.image_url}
          alt="Generated scene depiction"
          className="my-5 w-full rounded-lg border border-inherit/20"
        />
      )}

      {turn.audio_url && isVoiceOutputEnabled && (
        <button
          type="button"
          onClick={handleToggleAudio}
          className="my-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-inherit/20 hover:bg-surface-raised font-mono text-xs cursor-pointer transition-colors"
          title={isPlayingThisTurn ? "Stop narration" : "Play narration"}
        >
          <span>
            {isPlayingThisTurn ? (
              <IconPlayerPause size={14} stroke={1.5} />
            ) : (
              <IconPlayerPlay size={14} stroke={1.5} />
            )}
          </span>
          <span>{isPlayingThisTurn ? "Stop Narration" : "Play Narration"}</span>
        </button>
      )}

      {turn.chapter_delta && <ChapterSummaryStrip delta={turn.chapter_delta} />}

      <NarrationFlag turnId={turn.id} />
    </section>
  );
});
