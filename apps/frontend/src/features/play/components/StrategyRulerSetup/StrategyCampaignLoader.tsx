import React, { useState, useEffect } from "react";
import {
  IconCrown,
  IconSparkles,
  IconFeather,
  IconChevronLeft,
  IconChevronRight,
} from "@tabler/icons-react";
import {
  STRATEGY_TIPS,
  STRATEGY_LOADER_STAGES,
  StrategyTip,
} from "./strategyTips.constants";

export interface StrategyCampaignLoaderProps {
  status?: string;
  tipIntervalMs?: number;
  stageIntervalMs?: number;
  tips?: readonly StrategyTip[];
  className?: string;
}

export const StrategyCampaignLoader: React.FC<StrategyCampaignLoaderProps> = ({
  status,
  tipIntervalMs = 4000,
  stageIntervalMs = 3000,
  tips = STRATEGY_TIPS,
  className = "",
}) => {
  const [currentTipIndex, setCurrentTipIndex] = useState(0);
  const [currentStageIndex, setCurrentStageIndex] = useState(0);

  // Rotate tips every tipIntervalMs (default 4s)
  useEffect(() => {
    if (!tips.length) return;

    const interval = setInterval(() => {
      setCurrentTipIndex((prev) => (prev + 1) % tips.length);
    }, tipIntervalMs);

    return () => clearInterval(interval);
  }, [tips.length, tipIntervalMs]);

  // Rotate progressive stages if no fixed status prop is passed
  useEffect(() => {
    if (status) return;

    const interval = setInterval(() => {
      setCurrentStageIndex((prev) => (prev + 1) % STRATEGY_LOADER_STAGES.length);
    }, stageIntervalMs);

    return () => clearInterval(interval);
  }, [status, stageIntervalMs]);

  const displayedStatus =
    status ?? STRATEGY_LOADER_STAGES[currentStageIndex % STRATEGY_LOADER_STAGES.length];
  const activeTip = tips[currentTipIndex % tips.length];

  const handlePrevTip = () => {
    setCurrentTipIndex((prev) => (prev - 1 + tips.length) % tips.length);
  };

  const handleNextTip = () => {
    setCurrentTipIndex((prev) => (prev + 1) % tips.length);
  };

  return (
    <div
      role="status"
      aria-live="polite"
      className={`fixed inset-0 z-50 flex flex-col items-center justify-between p-6 sm:p-10 bg-[#EFE4C8] text-[#221A12] select-none overflow-hidden ${className}`}
    >
      {/* Atmospheric Mist & Watercolor Ambient Glows */}
      <div className="absolute -top-32 -left-32 w-96 h-96 bg-[#DCE7EA]/60 rounded-full blur-3xl pointer-events-none animate-pulse" />
      <div className="absolute top-1/2 -right-40 w-[30rem] h-[30rem] bg-[#ffdf9d]/35 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 left-1/3 w-80 h-80 bg-[#5E8A5A]/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#EFE4C8]/30 to-[#EFE4C8]/80 pointer-events-none" />

      {/* Top Header Stamp */}
      <header className="relative z-10 flex items-center justify-between w-full max-w-4xl pt-2">
        <div className="flex items-center gap-3 bg-[#F7F0DC]/80 backdrop-blur-sm px-4 py-1.5 rounded-full border border-[#3A3128]/15 shadow-sm">
          <IconFeather className="w-4 h-4 text-[#785A00]" />
          <span className="text-xs uppercase tracking-widest font-semibold text-[#46606E]">
            Wilds Grand Strategy • Inauguration
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-[#72787C] font-mono">
          <span className="w-2 h-2 rounded-full bg-[#5E8A5A] animate-ping" />
          <span>INITIALIZING CAMPAIGN</span>
        </div>
      </header>

      {/* Centerpiece: Golden Wax Seal & Progressive Status */}
      <main className="relative z-10 flex flex-col items-center justify-center text-center my-auto py-8">
        {/* Wax Seal Medallion */}
        <div
          data-testid="golden-wax-seal"
          className="relative group mb-8 flex items-center justify-center"
        >
          {/* Subtle Outer Pulsing Halo */}
          <div className="absolute w-36 h-36 rounded-full bg-[#D2A94A]/25 blur-xl animate-pulse" />

          {/* Golden Wax Seal Outer Ring */}
          <div className="relative w-28 h-28 sm:w-32 sm:h-32 rounded-full bg-gradient-to-br from-[#FED16E] via-[#D2A94A] to-[#785A00] p-[3px] shadow-[0_8px_32px_rgba(120,90,0,0.35)] transition-transform duration-700 ease-out hover:scale-105">
            {/* Scalloped Stamp Texture Border */}
            <div className="w-full h-full rounded-full border-2 border-dashed border-[#F7F0DC]/40 flex items-center justify-center bg-gradient-to-tr from-[#946F12] via-[#B88E28] to-[#ECC15F]">
              {/* Inner Medallion Well */}
              <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-gradient-to-b from-[#8C660D] to-[#614500] border border-[#FED16E]/70 shadow-inner flex flex-col items-center justify-center text-[#FED16E]">
                <IconCrown className="w-10 h-10 sm:w-12 sm:h-12 drop-shadow-[0_2px_4px_rgba(0,0,0,0.4)] animate-pulse" />
                <span className="text-[9px] font-mono tracking-widest uppercase font-bold text-[#FFDF9D]/90 mt-0.5">
                  ANNO 1042
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Dynamic Status Headline */}
        <div className="space-y-2 max-w-lg px-4">
          <h2 className="text-2xl sm:text-3xl font-serif font-semibold tracking-tight text-[#221A12] drop-shadow-sm">
            {displayedStatus}
          </h2>
          <p className="text-xs sm:text-sm text-[#42474B] font-serif italic">
            Gathering provincial tithes, charting trade paths, and unfurling the frontier.
          </p>
        </div>

        {/* Loading Progress Hairline */}
        <div className="w-48 h-1 bg-[#3A3128]/15 rounded-full overflow-hidden mt-6">
          <div className="h-full bg-gradient-to-r from-[#D2A94A] via-[#ECC15F] to-[#785A00] animate-[pulse_2s_ease-in-out_infinite] w-full" />
        </div>
      </main>

      {/* Footer: Curated Grand Strategy Tips Carousel */}
      <footer className="relative z-10 w-full max-w-2xl pb-4">
        <div
          data-testid="strategy-tip-card"
          className="bg-[#F7F0DC]/90 backdrop-blur-md border border-[#3A3128]/20 rounded-xl p-5 sm:p-6 shadow-xl transition-all duration-300"
        >
          {/* Header Row: Category Badge & Step Controls */}
          <div className="flex items-center justify-between pb-3 mb-2 border-b border-[#3A3128]/10 text-xs">
            <div className="flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-[#D2A94A]/20 flex items-center justify-center text-[#785A00]">
                <IconSparkles className="w-3.5 h-3.5" />
              </span>
              <span className="uppercase tracking-wider font-semibold text-[#46606E]">
                Royal Counsel • {activeTip?.category}
              </span>
            </div>

            {/* Quick manual navigation */}
            <div className="flex items-center gap-1 text-[#72787C]">
              <button
                type="button"
                onClick={handlePrevTip}
                aria-label="Previous tip"
                className="p-1 rounded hover:bg-[#3A3128]/10 hover:text-[#221A12] transition-colors cursor-pointer"
              >
                <IconChevronLeft className="w-4 h-4" />
              </button>
              <span className="font-mono text-[11px] px-1">
                {(currentTipIndex % tips.length) + 1} / {tips.length}
              </span>
              <button
                type="button"
                onClick={handleNextTip}
                aria-label="Next tip"
                className="p-1 rounded hover:bg-[#3A3128]/10 hover:text-[#221A12] transition-colors cursor-pointer"
              >
                <IconChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Rotating Tip Text */}
          <div
            key={activeTip?.id}
            className="min-h-[5rem] flex flex-col justify-center transition-opacity duration-300 animate-fade-in"
          >
            <blockquote className="font-serif text-base sm:text-lg text-[#221A12] leading-relaxed italic text-center">
              <span className="opacity-60 select-none mr-1">&ldquo;</span>
              {activeTip?.text}
              <span className="opacity-60 select-none ml-1">&rdquo;</span>
            </blockquote>
            {activeTip?.subtext && (
              <p className="text-xs text-[#72787C] text-center mt-2 font-sans">
                {activeTip.subtext}
              </p>
            )}
          </div>

          {/* Carousel Pagination Dots */}
          <div className="flex items-center justify-center gap-1.5 mt-3 pt-2">
            {tips.map((tip, idx) => (
              <button
                key={tip.id}
                type="button"
                aria-label={`Jump to tip ${idx + 1}`}
                onClick={() => setCurrentTipIndex(idx)}
                className={`h-1.5 rounded-full transition-all duration-300 cursor-pointer ${
                  idx === currentTipIndex % tips.length
                    ? "w-6 bg-[#D2A94A]"
                    : "w-2 bg-[#3A3128]/20 hover:bg-[#3A3128]/40"
                }`}
              />
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
};
