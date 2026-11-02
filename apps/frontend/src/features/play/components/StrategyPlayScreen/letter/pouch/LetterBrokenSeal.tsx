import React from "react";

export const LetterBrokenSeal: React.FC = () => (
  <div className="flex items-center gap-3">
    <div className="relative w-16 h-12 flex items-center justify-center filter drop-shadow-[1px_2px_3px_rgba(60,15,10,0.45)]">
      <div className="absolute -top-1 left-2 w-7 h-1.5 bg-[#8f271e]/70 -rotate-[25deg] rounded-full" />
      <div className="absolute -bottom-1 right-2 w-8 h-1.5 bg-[#8f271e]/70 rotate-[20deg] rounded-full" />
      <div className="absolute left-1 w-6 h-11 bg-tertiary rounded-l-full shadow-md flex items-center justify-end overflow-hidden border-t border-l border-[#d36f64]">
        <div className="w-6 h-6 rounded-full bg-[#7a2a22]/50 -mr-2" />
      </div>
      <div className="absolute right-1 w-6 h-11 bg-tertiary rounded-r-full shadow-md flex items-center justify-start overflow-hidden translate-x-1.5 translate-y-0.5 border-b border-r border-[#69211a]">
        <div className="w-6 h-6 rounded-full bg-[#7a2a22]/50 -ml-2" />
      </div>
      <span className="material-symbols-outlined text-tertiary-fixed text-[18px] relative z-20 rotate-12 pointer-events-none">
        lock_open_right
      </span>
    </div>
    <div className="text-[12px] font-body-sm text-on-surface-variant leading-tight">
      <p className="font-semibold text-tertiary">Broken wax seal</p>
      <p className="italic font-display text-[11px]">Unbroken during horse transit</p>
    </div>
  </div>
);
