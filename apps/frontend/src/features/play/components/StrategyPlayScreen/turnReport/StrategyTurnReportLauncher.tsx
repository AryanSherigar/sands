import React, { useEffect } from "react";
import { IconFileText } from "@tabler/icons-react";
import { useStrategyPlayStore } from "../../../stores/strategyPlay.store";
import type { StrategyTurnReportLauncherProps } from "./StrategyTurnReportLauncher.types";

function isEditableElement(target: EventTarget | null): boolean {
  if (!target || !(target instanceof HTMLElement)) return false;
  return target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;
}

function useReportKeyboardShortcut(onToggle: () => void): void {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.code !== "KeyR" && event.key.toLowerCase() !== "r") return;
      if (isEditableElement(event.target)) return;
      event.preventDefault();
      onToggle();
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onToggle]);
}

function renderUnreadBadge(hasUnread: boolean, count?: number) {
  if (!hasUnread || count === undefined || count <= 0) return null;
  return (
    <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-[#D2A94A]/25 text-[#785a00] border border-[#D2A94A]/60">
      {count} new
    </span>
  );
}

export const StrategyTurnReportLauncher: React.FC<StrategyTurnReportLauncherProps> = ({
  itemCount = 0,
  className = "",
}) => {
  const toggleTurnReport = useStrategyPlayStore((s) => s.toggleTurnReport);
  const hasUnreadTurnReport = useStrategyPlayStore((s) => s.hasUnreadTurnReport);
  const latestReport = useStrategyPlayStore((s) => s.latestReport);

  useReportKeyboardShortcut(toggleTurnReport);

  const title = latestReport?.seasonTitle
    ? `Open seasonal ledger for ${latestReport.seasonTitle}`
    : "Turn report [R]";

  const unreadClasses = hasUnreadTurnReport
    ? "animate-pulse shadow-[0_0_12px_rgba(210,169,74,0.45)] border-[#D2A94A]/60"
    : "border-[#3A3128]/30 shadow-md";

  return (
    <button
      type="button"
      title={title}
      onClick={toggleTurnReport}
      className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2 bg-[#F7F0DC]/95 border px-3.5 py-1.5 rounded-full backdrop-blur-sm text-sm font-medium text-[#3A3128] hover:bg-[#F3EAD3] transition-all cursor-pointer ${unreadClasses} ${className}`}
    >
      <IconFileText size={16} className="text-[#3A3128]/70" aria-hidden="true" />
      <span>Turn report</span>
      {renderUnreadBadge(hasUnreadTurnReport, itemCount)}
      <kbd className="text-[10px] text-[#7A6F62] font-mono">[R]</kbd>
    </button>
  );
};
