import {
  IconArrowLeft,
  IconCrown,
  IconNotebook,
  IconSettings,
  IconMoon,
  IconSun,
  IconWriting,
} from "@tabler/icons-react";
import { usePlayStore } from "../../../stores/play.store";
import { EBookAudioControl } from "../EBook/EBookAudioControl";
import { EBookNarrationVoiceControl } from "../EBook/EBookNarrationVoiceControl";
import { ReaderTypographyMenu } from "../EBook/ReaderTypographyMenu";
import { StatusHudContainer } from "../../StatusHud/StatusHudContainer";
import type { FantasyHeaderProps } from "./FantasyHeader.types";

function HeaderTopTier({
  scenarioTitle,
  folioTitle,
  turnNumber,
  isNarrating,
  isDossierOpen,
  dossierButton,
  onBack,
  onToggleDossier,
  onOpenChronicle,
}: Omit<FantasyHeaderProps, "onOpenCodex" | "onOpenMap">) {
  const isSepia = usePlayStore((state) => state.ebook_theme === "antique-sepia");
  const toggleTheme = usePlayStore((state) => state.toggleEBookTheme);
  return (
    <div className="flex items-center justify-between px-4 md:px-8 h-12 border-b border-[#382E25] bg-[#14110E]">
      <div className="flex items-center gap-3 min-w-0">
        <button
          type="button"
          onClick={onBack}
          title="Return to Chronicles"
          aria-label="Return to Chronicles"
          className="w-9 h-9 rounded flex items-center justify-center text-[#B5A593] hover:text-[#F5EEDB] hover:bg-[#201A15] border border-[#382E25] transition-colors"
        >
          <IconArrowLeft size={18} />
        </button>
        <div className="flex items-center gap-2 min-w-0 h-9">
          <IconCrown size={18} className="text-[#C5A059]" />
          <span className="font-serif text-[16px] font-semibold tracking-tight text-[#E6D5B8] truncate">
            {scenarioTitle}
          </span>
          <span className="hidden sm:inline-flex items-center gap-1.5 pl-2 border-l border-[#382E25] font-mono text-[11px] text-[#C5A059]">
            <span>✦</span> {folioTitle}
          </span>
        </div>
      </div>
      <div className="flex items-center gap-2.5 shrink-0">
        <div className="hidden sm:flex items-center justify-center gap-2 h-9 font-mono text-[11px]">
          <span className="text-[#C5A059] font-medium tracking-wider">
            CHRONICLE TURN {turnNumber}
          </span>
          <span className="w-1 h-1 rounded-full bg-[#4A3C2F]" />
          <span className="flex items-center gap-1 text-[#D4A373]">
            <IconWriting size={13} />
            {isNarrating ? "Inscribing" : "Inscribed"}
          </span>
        </div>
        <div className="flex items-center h-9 rounded bg-[#201A15] border border-[#4A3C2F] shadow-sm overflow-hidden">
          <button
            type="button"
            ref={dossierButton}
            onClick={onToggleDossier}
            aria-expanded={isDossierOpen}
            aria-controls="world-dossier"
            className="flex items-center justify-center gap-1.5 px-3 h-full hover:bg-[#2A221C] text-[#F5EEDB] text-xs font-serif transition-colors"
          >
            <IconNotebook size={15} className="text-[#C5A059]" />
            <span>World Dossier</span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#C5A059]" />
          </button>
        </div>
        <details className="relative fantasy-settings">
          <summary aria-label="Reader controls" className="w-11 h-11 flex items-center justify-center cursor-pointer text-[#C5A059]"><IconSettings size={18} /></summary>
          <div className="absolute right-0 top-full w-64 p-3 flex flex-wrap gap-2 bg-[#171310] border border-[#382E25] shadow-xl z-50">
            <StatusHudContainer /><EBookAudioControl /><EBookNarrationVoiceControl /><ReaderTypographyMenu isSepia={isSepia} fallbackFont="eb-garamond" />
            <button type="button" onClick={toggleTheme} className="min-h-11 px-2 text-[#EDE0CA]" aria-label={`Switch to ${isSepia ? "dark" : "sepia"} theme`}>{isSepia ? <IconMoon size={17} /> : <IconSun size={17} />}</button>
            <button type="button" onClick={onOpenChronicle} className="min-h-11 px-2 text-[#EDE0CA]">End Journey</button>
          </div>
        </details>
      </div>
    </div>
  );
}

function HeaderSubTier({
  onOpenCodex,
  onOpenMap,
}: Pick<FantasyHeaderProps, "onOpenCodex" | "onOpenMap">) {
  const handleScrollToPassage = () => {
    document.querySelector(".fantasy-turn-active, .fantasy-prologue")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="flex items-center overflow-x-auto px-4 md:px-8 h-10 bg-[#120F0D] border-b border-[#2E251E]">
      <nav aria-label="Folio Navigation" className="flex items-center gap-6 shrink-0 text-[13px]">
        <button
          type="button"
          onClick={handleScrollToPassage}
          className="text-[#E6D5B8] border-b-2 border-[#C5A059] pb-0.5 font-serif font-medium tracking-wide flex items-center gap-1 cursor-pointer"
        >
          <span className="text-[#C5A059] text-[10px]">❧</span>
          <span>Narrative Chamber</span>
        </button>
        <button
          type="button"
          onClick={onOpenCodex}
          className="text-[#B5A593] hover:text-[#F5EEDB] transition-colors font-serif cursor-pointer"
        >
          Codex &amp; Tomes
        </button>
        <button
          type="button"
          onClick={() => document.querySelector(".fantasy-turn")?.scrollIntoView({ behavior: "smooth" })}
          className="text-[#B5A593] hover:text-[#F5EEDB] transition-colors font-serif cursor-pointer"
        >
          Historical Ledger
        </button>
        {onOpenMap && (
          <button
            type="button"
            onClick={onOpenMap}
            className="text-[#B5A593] hover:text-[#F5EEDB] transition-colors font-serif cursor-pointer"
          >
            Cartography
          </button>
        )}
      </nav>
    </div>
  );
}

export function FantasyHeader(props: FantasyHeaderProps) {
  return (
    <header className="fixed top-0 left-0 right-0 z-40 bg-[#0C0C0E] border-b border-[#382E25] select-none">
      <HeaderTopTier {...props} />
      <HeaderSubTier
        onOpenCodex={props.onOpenCodex}
        onOpenMap={props.onOpenMap}
      />
    </header>
  );
}
