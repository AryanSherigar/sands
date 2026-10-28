import { useCallback, useEffect, useRef, useState } from "react";
import { usePlayStore } from "../../../stores/play.store";
import { IconArrowDown } from "@tabler/icons-react";
import { resolveNarrationFont } from "@/shared/constants/narration-fonts";
import { loadNarrationFont } from "@/shared/lib/font-loader";
import { EBookPrologueCard } from "./EBookPrologueCard";
import { EBookTurnEntry } from "./EBookTurnEntry";
import { PausedTurnNotice } from "./PausedTurnNotice";
import { StreamingNarration } from "./StreamingNarration";
import { useSanityBand } from "../../../hooks/useSanityBand";
import { useReaderFlicker } from "../../../hooks/useReaderFlicker";
import { ReaderVignetteContainer } from "../../ReaderEffects/ReaderVignetteContainer";

const EERIE_FONT_ID = "special-elite";

export function EBookCanvas() {
  const playthrough = usePlayStore((s) => s.playthrough);
  const isNarrating = usePlayStore((s) => s.is_narrating);
  const openActionDrawer = usePlayStore((s) => s.openActionDrawer);
  const readerFontOverride = usePlayStore((s) => s.reader_font_override);

  const { band: sanityBand } = useSanityBand();
  const isDistorting = sanityBand !== "none";
  const isFlickering = useReaderFlicker();

  useEffect(() => {
    if (isDistorting) loadNarrationFont(EERIE_FONT_ID);
  }, [isDistorting]);

  const scenarioFont = playthrough?.narration_font;
  const activeFont = resolveNarrationFont(readerFontOverride ?? scenarioFont);

  useEffect(() => {
    loadNarrationFont(activeFont.id);
  }, [activeFont.id]);

  const hasOpenRuleCheck = usePlayStore((s) => s.active_rule_check !== null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);
  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    if (containerRef.current) {
      containerRef.current.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior,
      });
    }
  }, []);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    setShowScrollBottom(scrollHeight - scrollTop - clientHeight > 120);
  };

  useEffect(() => {
    if (hasOpenRuleCheck) scrollToBottom("smooth");
  }, [hasOpenRuleCheck, scrollToBottom]);

  useEffect(() => {
    if (isNarrating) {
      scrollToBottom("auto");
    } else if (playthrough?.turns.length) {
      scrollToBottom("smooth");
    }
  }, [isNarrating, playthrough?.turns.length, scrollToBottom]);

  if (!playthrough) return null;

  return (
    <main
      ref={containerRef}
      onScroll={handleScroll}
      data-sanity={isDistorting ? sanityBand : undefined}
      className={`${isFlickering ? "power-flicker " : ""}relative flex-1 w-full h-full overflow-y-auto px-4 sm:px-8 md:px-12 pt-6 ${hasOpenRuleCheck ? "pb-104" : "pb-56"} scrollbar-minimal selection:bg-surface-raised selection:text-content`}
    >
      <ReaderVignetteContainer />
      <div className="max-w-[68ch] w-full mx-auto min-h-full flex flex-col">
        {/* Turn 0: Frontispiece / Prologue Card */}
        <EBookPrologueCard
          premise={playthrough.opening_premise}
          onStartAction={openActionDrawer}
        />

        {/* Turned Chapters Feed */}
        {playthrough.turns.map((turn, index) => (
          <EBookTurnEntry
            key={turn.id}
            turn={turn}
            turnIndex={index}
            isLatest={index === playthrough.turns.length - 1}
            shouldDistort={isDistorting}
          />
        ))}

        {/* Live Streaming Chapter */}
        {isNarrating && (
          <StreamingNarration
            chapterNumber={playthrough.turns.length + 1}
            characterName={playthrough.character_name}
            fontClass={activeFont.fontClass}
            shouldDistort={isDistorting}
            playthroughId={playthrough.playthrough_id}
            onScrollToBottom={scrollToBottom}
          />
        )}

        <PausedTurnNotice />
      </div>

      {/* Floating Bookmark: Jump to Latest */}
      {showScrollBottom && (
        <button
          type="button"
          onClick={() => scrollToBottom("smooth")}
          className="fixed bottom-24 right-6 py-2 px-3 rounded-md border border-border-strong bg-surface-overlay text-content shadow-float font-mono text-xs font-medium hover:bg-surface-raised transition-all cursor-pointer z-30 flex items-center gap-1.5"
        >
          <span>Latest Chapter</span>
          <IconArrowDown size={14} stroke={1.5} />
        </button>
      )}
    </main>
  );
}
