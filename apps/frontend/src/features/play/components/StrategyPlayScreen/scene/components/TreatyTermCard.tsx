import React from "react";
import type { TreatyTermCardProps, TreatyTermTone } from "./TreatyTermCard.types";

interface ToneClasses {
  dot: string;
  icon: string;
  badge: string;
}

const TONE_CLASSES: Record<TreatyTermTone, ToneClasses> = {
  green: {
    dot: "bg-meadow-green",
    icon: "text-meadow-green",
    badge: "bg-primary-fixed text-on-primary-fixed",
  },
  amber: {
    dot: "bg-amber-500",
    icon: "text-amber-500",
    badge: "bg-amber-500/20 text-amber-300",
  },
  sky: {
    dot: "bg-sky-500",
    icon: "text-sky-500",
    badge: "bg-sky-500/20 text-sky-300",
  },
  purple: {
    dot: "bg-purple-500",
    icon: "text-purple-500",
    badge: "bg-purple-500/20 text-purple-300",
  },
  rose: {
    dot: "bg-[#A8483E]",
    icon: "text-[#A8483E]",
    badge: "bg-[#A8483E]/20 text-rose-300",
  },
};

export const TreatyTermCard: React.FC<TreatyTermCardProps> = ({ view }) => {
  const tone = TONE_CLASSES[view.tone];
  return (
    <div className="p-3.5 bg-surface-container rounded-xl shadow-sm border border-outline-variant/30">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${tone.dot}`} />
          <span className={`material-symbols-outlined text-[18px] ${tone.icon}`}>
            {view.icon}
          </span>
          <span className="font-serif text-base font-semibold text-on-surface">
            {view.title}
          </span>
        </div>
        <span
          className={`font-sans text-[10px] uppercase px-2 py-0.5 font-bold rounded ${tone.badge}`}
        >
          {view.badge}
        </span>
      </div>
      <p className="font-sans text-xs text-outline mt-1.5 ml-4">{view.detail}</p>
    </div>
  );
};
