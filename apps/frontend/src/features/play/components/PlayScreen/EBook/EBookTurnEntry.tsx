import { memo } from "react";
import { IconPlayerPause, IconPlayerPlay } from "@tabler/icons-react";
import { usePlayStore } from "../../../stores/play.store";
import { resolveNarrationFont } from "@/shared/constants/narration-fonts";
import { useVoiceOutputPreference } from "@/shared/hooks/useVoiceOutputPreference";
import { ChapterSummaryStrip } from "./ChapterSummaryStrip";
import { HighlightedParagraph } from "./HighlightedParagraph";
import { NarrationFlag } from "../NarrationFlag/NarrationFlag";
import type { EBookTurnEntryProps } from "./ebook.types";

function getTurnHeaderLabel(isFantasy: boolean, isLatest: boolean, turnIndex: number): string {
  if (!isFantasy) return `Chapter ${turnIndex + 1}`;
  return isLatest ? `CHRONICLE TURN ${turnIndex + 1} · ACTIVE PASSAGE` : `ENTRY ${turnIndex + 1}`;
}

function getArticleClass(isFantasy: boolean, isLatest: boolean): string {
  if (!isFantasy) return "prose-book";
  return isLatest
    ? "font-serif text-[20px] text-[#F5EEDB] leading-[36px] tracking-[0.01em] space-y-6"
    : "font-serif text-[18px] text-[#B5A593] leading-relaxed italic space-y-4";
}

export const EBookTurnEntry = memo(function EBookTurnEntry({
  turn,
  turnIndex,
  isLatest,
  isFantasy = false,
  shouldDistort = false,
  shouldHideImage = false,
}: EBookTurnEntryProps) {
  const isSilentContinue = turn.action_text === "Continue the story.";
  const characterName = usePlayStore((s) => s.playthrough?.character_name ?? "Adventurer");
  const hasScenePortraits = usePlayStore((s) => s.playthrough?.genre_tags?.[0] === "Slice of Life");
  const playthroughId = usePlayStore((s) => s.playthrough?.playthrough_id ?? "");
  const scenarioFont = usePlayStore((s) => s.playthrough?.narration_font);
  const readerFontOverride = usePlayStore((s) => s.reader_font_override);
  const activeFont = resolveNarrationFont(readerFontOverride ?? scenarioFont ?? (isFantasy ? "eb-garamond" : undefined));
  const paragraphs = turn.narration_text.split(/\n\s*\n/).filter(Boolean);
  const isPlayingAudio = usePlayStore((s) => s.playing_audio_turn_id === turn.id);
  const playTurnAudio = usePlayStore((s) => s.playTurnAudio);
  const stopTurnAudio = usePlayStore((s) => s.stopTurnAudio);
  const { isVoiceOutputEnabled } = useVoiceOutputPreference();

  const handleToggleAudio = () => {
    if (isPlayingAudio) stopTurnAudio();
    else if (turn.audio_url) playTurnAudio(turn.id, turn.audio_url, hasScenePortraits);
  };

  const formattedTime = new Date(turn.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <section className={isFantasy ? `fantasy-turn relative pl-7 ${isLatest ? "fantasy-turn-active mb-12" : "mb-10 opacity-75 hover:opacity-100 group"}` : "my-8 pt-6 border-t border-inherit/20 first:border-t-0"}>
      {isFantasy && (
        <>
          <div className={`absolute left-2.5 top-0 bottom-0 w-[1px] ${isLatest ? "bg-[#C5A059]/40" : "bg-[#382E25] group-hover:bg-[#C5A059]/50 transition-colors"}`} />
          {isLatest ? (
            <div className="absolute left-[5px] top-2 w-3 h-3 rounded-full bg-[#181512] border-2 border-[#C5A059] flex items-center justify-center">
              <div className="w-1 h-1 rounded-full bg-[#C5A059]" />
            </div>
          ) : (
            <div className="absolute left-[7px] top-1.5 w-2 h-2 rounded-full border border-[#4A3C2F] bg-[#1A1612]" />
          )}
        </>
      )}

      <header className="flex items-center justify-between font-mono text-xs opacity-80 mb-4 tracking-wider">
        <span className={isFantasy ? "text-[#C5A059] font-medium flex items-center gap-1.5 uppercase" : "uppercase"}>
          {getTurnHeaderLabel(isFantasy, isLatest, turnIndex)}
        </span>
        <span className={isFantasy ? "text-[#8C7A6B] text-[10px]" : ""}>{formattedTime}</span>
      </header>

      {!isSilentContinue && (
        <aside className={isFantasy ? "p-3 mb-4 rounded bg-[#171310] border border-[#382E25] font-sans text-[13px] text-[#B5A593]" : "mb-5 pl-4 border-l-2 border-border-strong italic font-serif text-sm opacity-80"}>
          <span className={isFantasy ? "text-[#C5A059] font-serif font-semibold text-[12px] tracking-wider uppercase mr-2" : "font-mono text-xs not-italic opacity-70 mr-1.5 uppercase font-medium"}>
            {isFantasy ? "Your Action:" : `${characterName} (${turn.action_mode}):`}
          </span>
          "{turn.action_text}"
        </aside>
      )}

      <article className={getArticleClass(isFantasy, isLatest)}>
        {paragraphs.map((para: string, idx: number) => (
          <HighlightedParagraph
            key={idx}
            paragraph={para}
            isFirst={!isFantasy && idx === 0}
            fontClass={activeFont.fontClass}
            distortion={shouldDistort ? { playthroughId, turnNumber: turnIndex + 1, paragraphIndex: idx, isComplete: true } : undefined}
          />
        ))}
      </article>

      {turn.image_url && !shouldHideImage && (
        <img src={turn.image_url} alt="Generated scene depiction" className="my-5 w-full rounded-lg border border-inherit/20" />
      )}

      {turn.audio_url && isVoiceOutputEnabled && (
        <button
          type="button"
          onClick={handleToggleAudio}
          className="my-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-inherit/20 hover:bg-surface-raised font-mono text-xs cursor-pointer transition-colors"
          title={isPlayingAudio ? "Stop narration" : "Play narration"}
        >
          {isPlayingAudio ? <IconPlayerPause size={14} stroke={1.5} /> : <IconPlayerPlay size={14} stroke={1.5} />}
          <span>{isPlayingAudio ? "Stop Narration" : "Play Narration"}</span>
        </button>
      )}

      {turn.chapter_delta && <ChapterSummaryStrip delta={turn.chapter_delta} />}
      <NarrationFlag turnId={turn.id} />
    </section>
  );
});
