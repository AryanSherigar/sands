import React from "react";

export const LetterStillLifeAccents: React.FC = () => (
  <div className="absolute top-4 right-10 flex items-center gap-6 pointer-events-none opacity-85 z-0">
    {/* Beeswax Taper Candle with Soft Animated Flame */}
    <div className="relative flex flex-col items-center">
      <div className="w-3 h-5 rounded-full bg-secondary/80 blur-[2px] animate-pulse shadow-[0_0_16px_6px_rgba(254,209,110,0.65)]" />
      <div className="w-2 h-1 bg-tertiary rounded-t-sm -mt-0.5" />
      <div className="w-4 h-8 bg-parchment-base rounded-t-sm shadow-inner" />
      <div className="w-7 h-1.5 bg-surface-variant rounded-full -mt-0.5 shadow-sm" />
    </div>
    {/* Brass Inkwell & Goose Quill Rest Silhouette */}
    <div className="hidden xl:flex items-end gap-3 opacity-70">
      <div className="flex flex-col items-center">
        <div className="w-1.5 h-16 bg-[#523d24]/60 -rotate-12 origin-bottom-right rounded-t-full" />
        <div className="w-8 h-5 bg-[#c2b28c] rounded-t-lg rounded-b-sm shadow-inner flex items-center justify-center">
          <div className="w-3 h-1.5 bg-[#3a3128] rounded-full" />
        </div>
      </div>
      {/* Vermilion Wax Stick Fragment */}
      <div className="w-10 h-3 bg-tertiary rounded-sm shadow-sm rotate-6" />
    </div>
  </div>
);
