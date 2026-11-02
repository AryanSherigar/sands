import React from "react";
import type { DocketChoice } from "../../../../types/letterScene.types";
import type { LetterReplyDocketsFlapProps } from "./LetterPouchStage.types";

interface DocketOption {
  choice: DocketChoice;
  title: string;
  icon: string;
  shortcut: string;
  description: string;
  containerClass: string;
  iconClass: string;
  kbdClass: string;
  textClass: string;
}

const DECLINE_OPTION: DocketOption = {
  choice: "decline",
  title: "Decline to answer",
  icon: "block",
  shortcut: "4",
  description: "Leave the letter unanswered. Nothing changes between you.",
  containerClass:
    "bg-surface-container-high hover:bg-surface-container-highest text-on-surface shadow-xs border border-[#d6c7a7]",
  iconClass: "text-on-surface-variant",
  kbdClass: "bg-[#dfcfaf] text-on-surface-variant",
  textClass: "text-on-surface-variant",
};

const buildDocketOptions = (senderName: string, isDeclinable: boolean): DocketOption[] => [
  {
    choice: "write",
    title: "Write it myself",
    icon: "history_edu",
    shortcut: "1",
    description: `Take up the quill and pen your own words directly to ${senderName}.`,
    containerClass: "bg-primary-container hover:bg-primary text-on-primary shadow-md",
    iconClass: "text-sky-mist",
    kbdClass: "bg-[#324854] text-sky-mist",
    textClass: "text-sky-mist/90",
  },
  {
    choice: "scribe",
    title: "Ask my scribe",
    icon: "stylus_note",
    shortcut: "2",
    description: "Tell the scribe what you want; they will draft it for your review.",
    containerClass: "bg-[#D2A94A] hover:bg-[#c2983b] text-[#2c2004] shadow-md",
    iconClass: "text-[#543b00]",
    kbdClass: "bg-[#785a00] text-white",
    textClass: "text-[#4d3806]",
  },
  {
    choice: "aside",
    title: "Set it aside",
    icon: "folder_open",
    shortcut: "3",
    description: "Place the letter back in the correspondence tray.",
    containerClass: "bg-surface-container-high hover:bg-surface-container-highest text-on-surface shadow-xs border border-[#d6c7a7]",
    iconClass: "text-on-surface-variant",
    kbdClass: "bg-[#dfcfaf] text-on-surface-variant",
    textClass: "text-on-surface-variant",
  },
  ...(isDeclinable ? [DECLINE_OPTION] : []),
];

function DocketsHeader({ senderName }: { senderName: string }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between pb-2 border-b border-on-surface/10">
        <h2 className="font-headline-sm text-title-md font-semibold text-on-surface">{`Reply to ${senderName}`}</h2>
        <span className="material-symbols-outlined text-secondary text-[20px]">mark_chat_read</span>
      </div>
      <div className="flex items-center gap-2 p-2.5 rounded-lg bg-surface-container-low/90 text-on-surface-variant border border-outline-variant/30">
        <span className="material-symbols-outlined text-[16px] text-secondary flex-shrink-0">hourglass_empty</span>
        <p className="font-body-sm text-[12px] leading-snug">No hurry. Letters are answered at your pace.</p>
      </div>
    </div>
  );
}

function DocketButton({
  option,
  onSelect,
}: {
  option: DocketOption;
  onSelect: (choice: DocketChoice) => void;
}) {
  const handleClick = () => {
    onSelect(option.choice);
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`group relative w-full text-left p-3.5 rounded-lg transition-all active:translate-y-0.5 cursor-pointer ${option.containerClass}`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={`material-symbols-outlined text-[18px] ${option.iconClass}`}>{option.icon}</span>
          <span className="font-title-md text-[15px] font-semibold tracking-wide">{option.title}</span>
        </div>
        <kbd className={`px-1.5 py-0.5 rounded text-[11px] font-stat-numeric font-bold ${option.kbdClass}`}>
          {option.shortcut}
        </kbd>
      </div>
      <p className={`mt-1.5 text-[11px] font-body-sm leading-snug ${option.textClass}`}>
        {option.description}
      </p>
    </button>
  );
}

export const LetterReplyDocketsFlap: React.FC<LetterReplyDocketsFlapProps> = ({
  senderName,
  isDeclinable,
  onSelect,
}) => (
  <aside aria-label="Reply Options" className="lg:col-span-3 flex flex-col justify-between rounded-xl bg-gradient-to-bl from-[#ebe1c7] to-[#dfd1ae] p-5 shadow-inner border border-[#d2c29c]/80 relative overflow-hidden order-3">
    <div className="flex flex-col gap-3 relative z-10">
      <DocketsHeader senderName={senderName} />
      <div className="flex flex-col gap-2.5 pt-1">
        {buildDocketOptions(senderName, isDeclinable).map((opt) => (
          <DocketButton key={opt.choice} option={opt} onSelect={onSelect} />
        ))}
      </div>
    </div>
  </aside>
);
