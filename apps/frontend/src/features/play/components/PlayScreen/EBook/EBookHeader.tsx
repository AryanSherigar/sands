import { IconArrowLeft, IconBook, IconMoon, IconSun } from "@tabler/icons-react";
import { usePlayStore } from "../../../stores/play.store";
import { EBookHeaderProps } from "./ebook.types";
import { EBookAudioControl } from "./EBookAudioControl";
import { EBookNarrationVoiceControl } from "./EBookNarrationVoiceControl";
import { ReaderTypographyMenu } from "./ReaderTypographyMenu";
import { FeedbackButton } from "../FeedbackButton/FeedbackButton";
import { StatusHudContainer } from "../../StatusHud/StatusHudContainer";
import { StatusHudStripContainer } from "../../StatusHud/StatusHudStripContainer";

export function EBookHeader({
  onBack,
  onOpenCodex,
  onOpenChronicle,
}: EBookHeaderProps) {
  const playthrough = usePlayStore((s) => s.playthrough);
  const theme = usePlayStore((s) => s.ebook_theme);
  const toggleEBookTheme = usePlayStore((s) => s.toggleEBookTheme);

  const isSepia = theme === "antique-sepia";
  const headerStyle = isSepia
    ? "bg-[#faf4e8]/95 border-[#d8c7a8] text-[#2c2217]"
    : "bg-surface-sunken/95 border-border-subtle text-content";

  const totalTurns = playthrough?.turns.length ?? 0;

  return (
    <div className="sticky top-0 z-30">
      <header
        className={`relative z-10 w-full h-14 border-b backdrop-blur-md px-4 flex items-center justify-between transition-colors ${headerStyle}`}
      >
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className="p-1.5 rounded-lg hover:bg-surface-raised font-mono text-xs flex items-center gap-1.5 cursor-pointer opacity-75 hover:opacity-100"
            title="Return to Discovery"
            aria-label="Return to Discovery"
          >
            <IconArrowLeft size={16} stroke={1.5} />
            <span className="hidden sm:inline">Discovery</span>
          </button>

          <div className="h-4 w-px bg-inherit/30 hidden sm:block" />

          <div className="truncate max-w-[200px] sm:max-w-xs md:max-w-md">
            <h1 className="font-serif text-sm sm:text-base font-bold truncate leading-tight">
              {playthrough?.scenario_title || "Chronicle"}
            </h1>
            <p className="font-mono text-[10px] opacity-60 hidden sm:block">
              by {playthrough?.creator_name || "Unknown Author"}
            </p>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-2 font-mono text-xs opacity-75">
          <span>Chapter {totalTurns + 1}</span>
          <span>•</span>
          <span className="text-success text-[11px]">Auto-saved</span>
        </div>

        <div className="flex items-center gap-1.5 sm:gap-2">
          <StatusHudContainer />
          <FeedbackButton />
          <EBookAudioControl />
          <EBookNarrationVoiceControl />
          <ReaderTypographyMenu isSepia={isSepia} />

          <button
            type="button"
            onClick={toggleEBookTheme}
            className="p-1.5 px-2.5 rounded-xl border border-inherit/20 hover:bg-surface-raised font-mono text-xs flex items-center gap-1.5 cursor-pointer transition-colors"
            title={`Switch to ${isSepia ? "Dark" : "Sepia"} theme`}
            aria-label={`Switch to ${isSepia ? "Dark" : "Sepia"} theme`}
          >
            {isSepia ? (
              <IconMoon size={16} stroke={1.5} />
            ) : (
              <IconSun size={16} stroke={1.5} />
            )}
            <span className="hidden sm:inline">
              {isSepia ? "Dark" : "Sepia"}
            </span>
          </button>

          <button
            type="button"
            onClick={onOpenCodex}
            className="p-1.5 px-2.5 rounded-xl border border-inherit/20 hover:bg-surface-raised font-mono text-xs flex items-center gap-1.5 cursor-pointer transition-colors"
            title="World Codex"
            aria-label="World Codex"
          >
            <IconBook size={16} stroke={1.5} />
            <span className="hidden md:inline">Codex</span>
          </button>

          <button
            type="button"
            onClick={onOpenChronicle}
            className={`p-1.5 px-2.5 rounded-xl border font-mono text-xs font-semibold cursor-pointer transition-colors ${
              isSepia
                ? "bg-[#e2d5be]/40 hover:bg-[#e2d5be]/70 border-[#d8c7a8] text-[#2c2217]"
                : "border-border-strong bg-surface-raised hover:bg-surface-overlay text-content"
            }`}
            title="Complete and Recap Playthrough"
          >
            End Journey
          </button>
        </div>
      </header>
      <StatusHudStripContainer themeClassName={headerStyle} />
    </div>
  );
}
