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
import { FantasyScenePlate } from "../Fantasy/FantasyScenePlate";
import type { EBookCanvasProps } from "./ebook.types";

const EERIE_FONT_ID = "special-elite";

export function EBookCanvas({ isFantasy = false, sceneImage = null, children }: EBookCanvasProps = {}) {
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
  const activeFont = resolveNarrationFont(readerFontOverride ?? scenarioFont ?? (isFantasy ? "eb-garamond" : undefined));

  useEffect(() => {
    loadNarrationFont(activeFont.id);
  }, [activeFont.id]);

  const hasOpenRuleCheck = usePlayStore((s) => s.active_rule_check !== null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);
  const isFollowing = useRef(true);
  const priorFantasyTurnCount = useRef<number | null>(null);
  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    if (isFantasy) {
      window.scrollTo({ top: document.documentElement.scrollHeight, behavior });
    } else if (containerRef.current) {
      containerRef.current.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior,
      });
    }
  }, [isFantasy]);

  const handleScroll = useCallback(() => {
    const container = isFantasy ? document.documentElement : containerRef.current;
    if (!container) return;
    const scrollTop = isFantasy ? window.scrollY : container.scrollTop;
    const { scrollHeight, clientHeight } = container;
    setShowScrollBottom(scrollHeight - scrollTop - clientHeight > 120);
    isFollowing.current = scrollHeight - scrollTop - clientHeight <= 120;
  }, [isFantasy]);

  useEffect(() => {
    if (!isFantasy) return;
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [isFantasy, handleScroll]);

  const followStream = useCallback((behavior: ScrollBehavior = "smooth") => {
    if (!isFantasy || isFollowing.current) scrollToBottom(behavior);
  }, [isFantasy, scrollToBottom]);

  useEffect(() => {
    if (hasOpenRuleCheck) scrollToBottom("smooth");
  }, [hasOpenRuleCheck, scrollToBottom]);

  useEffect(() => {
    if (isFantasy && playthrough) {
      if (priorFantasyTurnCount.current === null) {
        priorFantasyTurnCount.current = playthrough.turns.length;
        if (!isNarrating) return;
      }
      const countChanged = priorFantasyTurnCount.current !== playthrough.turns.length;
      priorFantasyTurnCount.current = playthrough.turns.length;
      if (!isNarrating && !countChanged) return;
    }
    if (isNarrating) {
      followStream("auto");
    } else if (playthrough?.turns.length) {
      followStream("smooth");
    }
  }, [isFantasy, isNarrating, playthrough, playthrough?.turns.length, followStream]);

  if (!playthrough) return null;

  return (
    <main
      ref={containerRef}
      onScroll={handleScroll}
      style={isFantasy && !hasOpenRuleCheck ? { paddingBottom: "4rem" } : undefined}
      data-sanity={isDistorting ? sanityBand : undefined}
      className={`${isFlickering ? "power-flicker " : ""}relative flex-1 w-full h-full overflow-y-auto px-4 sm:px-8 md:px-12 pt-6 ${hasOpenRuleCheck ? "pb-104" : "pb-56"} scrollbar-minimal selection:bg-surface-raised selection:text-content`}
    >
      <ReaderVignetteContainer />
      <div className={`max-w-[68ch] w-full mx-auto min-h-full flex flex-col ${isFantasy ? "fantasy-reading-column" : ""}`}>
        {sceneImage && (
          isFantasy ? (
            <FantasyScenePlate url={sceneImage.url} />
          ) : (
            <section className="fantasy-scene-plate mb-8 relative rounded-xl overflow-hidden border border-border-subtle bg-surface-inset">
              <div className="relative w-full aspect-[16/9] overflow-hidden">
                <img src={sceneImage.url} alt="Scene illustration" className="w-full h-full object-cover object-center" />
                <div className="absolute inset-0 bg-gradient-to-t from-surface via-transparent to-black/30 pointer-events-none" />
              </div>
            </section>
          )
        )}
        {/* Turn 0: Frontispiece / Prologue Card */}
        <EBookPrologueCard
          isFantasy={isFantasy}
          premise={playthrough.opening_premise}
          onStartAction={openActionDrawer}
        />

        {/* Turned Chapters Feed */}
        {playthrough.turns.map((turn, index) => (
          <EBookTurnEntry
            key={turn.id}
            isFantasy={isFantasy}
            turn={turn}
            turnIndex={index}
            isLatest={index === playthrough.turns.length - 1}
            shouldDistort={isDistorting}
            shouldHideImage={sceneImage?.turnId === turn.id}
          />
        ))}

        {/* Live Streaming Chapter */}
        {isNarrating && (
          <StreamingNarration
            isFantasy={isFantasy}
            chapterNumber={playthrough.turns.length + 1}
            characterName={playthrough.character_name}
            fontClass={activeFont.fontClass}
            shouldDistort={isDistorting}
            playthroughId={playthrough.playthrough_id}
            onScrollToBottom={followStream}
          />
        )}

        <PausedTurnNotice />
        {children}
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
