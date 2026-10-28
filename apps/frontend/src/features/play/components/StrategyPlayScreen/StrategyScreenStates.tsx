import React from "react";

const SCREEN_CLASS =
  "min-h-dvh w-full bg-[#EFE4C8] flex flex-col items-center justify-center space-y-3 font-serif";

export const StrategyLoadingState: React.FC = () => (
  <main className={SCREEN_CLASS}>
    <div className="w-10 h-10 border-2 border-[#46606E]/20 border-t-[#46606E] rounded-full animate-spin" />
    <p className="text-xs uppercase tracking-widest text-[#72787C]">Loading Campaign...</p>
  </main>
);

interface StrategyErrorStateProps {
  onRetry: () => void;
}

export const StrategyErrorState: React.FC<StrategyErrorStateProps> = ({ onRetry }) => (
  <main className={SCREEN_CLASS}>
    <p className="text-sm text-[#221A12]">The campaign could not be loaded.</p>
    <button
      type="button"
      onClick={onRetry}
      className="px-4 py-2 rounded-lg bg-[#46606E] text-white text-xs font-bold cursor-pointer"
    >
      Try again
    </button>
  </main>
);
