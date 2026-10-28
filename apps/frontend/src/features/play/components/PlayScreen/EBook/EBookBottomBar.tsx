import { usePlayStore } from "../../../stores/play.store";
import { EBookBottomBarProps } from "./ebook.types";

export function EBookBottomBar({
  isSpectator,
  canAct = true,
  waitingOnLabel,
  isEnded = false,
  hasRulesPanel = false,
}: EBookBottomBarProps) {
  const theme = usePlayStore((s) => s.ebook_theme);
  const isSepia = theme === "antique-sepia";
  const positionClass = hasRulesPanel
    ? "left-1/2 lg:left-[calc(50%-8rem)]"
    : "left-1/2";

  const barStyle = isSepia
    ? "bg-[#faf4e8]/95 border-[#d8c7a8] text-[#2c2217] shadow-xl shadow-amber-900/10"
    : "bg-black/85 border-zinc-800/90 text-zinc-200 shadow-2xl shadow-black";

  if (isSpectator) {
    return (
      <footer
        className={`fixed bottom-4 ${positionClass} -translate-x-1/2 z-30 px-4 w-full max-w-lg opacity-60 hover:opacity-100 transition-opacity duration-300`}
      >
        <div
          className={`p-3 rounded-full border text-center font-mono text-xs backdrop-blur-md ${barStyle}`}
        >
          You are currently spectating this chronicle (Read-Only)
        </div>
      </footer>
    );
  }

  if (isEnded) {
    return (
      <footer
        className={`fixed bottom-4 ${positionClass} -translate-x-1/2 z-30 px-4 w-full max-w-lg opacity-60 hover:opacity-100 transition-opacity duration-300`}
      >
        <div
          className={`p-3 rounded-full border text-center font-mono text-xs backdrop-blur-md ${barStyle}`}
        >
          This chronicle has ended
        </div>
      </footer>
    );
  }

  if (!canAct) {
    return (
      <footer
        className={`fixed bottom-4 ${positionClass} -translate-x-1/2 z-30 px-4 w-full max-w-lg opacity-60 hover:opacity-100 transition-opacity duration-300`}
      >
        <div
          className={`p-3 rounded-full border text-center font-mono text-xs backdrop-blur-md ${barStyle}`}
        >
          Waiting for {waitingOnLabel ?? "another player"}...
        </div>
      </footer>
    );
  }

  return null;
}
