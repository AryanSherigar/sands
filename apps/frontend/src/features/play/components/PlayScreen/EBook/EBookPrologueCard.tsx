import { usePlayStore } from "../../../stores/play.store";
import { resolveNarrationFont } from "@/shared/constants/narration-fonts";
import { READER_FONT_SIZE_CLASSES } from "@/shared/constants/reader-preferences";
import { EBookPrologueCardProps } from "./ebook.types";

function PrologueHeader({ bannerStyle }: { bannerStyle: string }) {
  return (
    <div className="flex items-center justify-between pb-4 border-b border-inherit/20 mb-5">
      <div
        className={`font-mono text-xs uppercase tracking-widest font-semibold flex items-center gap-2 ${bannerStyle}`}
      >
        <span>✦</span>
        <span>Prologue</span>
        <span>✦</span>
      </div>
    </div>
  );
}

function PrologueFooter({ onStartAction }: { onStartAction: () => void }) {
  return (
    <div className="flex items-center justify-end pt-3 border-t border-inherit/20 text-xs font-mono opacity-80">
      <button
        type="button"
        onClick={onStartAction}
        className="hover:underline font-semibold cursor-pointer opacity-90 hover:opacity-100"
      >
        Begin First Action →
      </button>
    </div>
  );
}

export function EBookPrologueCard({
  premise,
  onStartAction,
}: EBookPrologueCardProps) {
  const theme = usePlayStore((s) => s.ebook_theme);
  const scenarioFont = usePlayStore((s) => s.playthrough?.narration_font);
  const readerFontOverride = usePlayStore((s) => s.reader_font_override);
  const readerFontSize = usePlayStore((s) => s.reader_font_size);
  const activeFont = resolveNarrationFont(readerFontOverride ?? scenarioFont);
  const isSepia = theme === "antique-sepia";

  const cardStyle = isSepia
    ? "bg-[#faf4e8]/80 border-[#d8c7a8] text-[#2c2217]"
    : "bg-surface-sunken/80 border-border-subtle text-content";

  const bannerStyle = isSepia
    ? "text-[#8c6b45] border-[#d8c7a8]"
    : "text-content-muted border-border-subtle";

  return (
    <article
      className={`p-6 md:p-8 rounded-2xl border shadow-xs my-6 transition-colors ${cardStyle}`}
    >
      <PrologueHeader bannerStyle={bannerStyle} />
      <p
        className={`${activeFont.fontClass} ${READER_FONT_SIZE_CLASSES[readerFontSize]} leading-relaxed italic mb-6 whitespace-pre-line`}
      >
        "{premise}"
      </p>
      <PrologueFooter onStartAction={onStartAction} />
    </article>
  );
}
