import React, { useState, useEffect } from "react";

interface DramaticSetupLoaderProps {
  scenarioTitle?: string;
  onComplete?: () => void;
  isReady?: boolean;
}

const LOADING_PHRASES = [
  "Weaving the threads of fate...",
  "Binding choices into reality...",
  "Synthesizing initial world state...",
  "Awakening the AI Narrator...",
  "Opening the portal...",
];

export const DramaticSetupLoader: React.FC<DramaticSetupLoaderProps> = ({
  scenarioTitle,
  onComplete,
  isReady = true,
}) => {
  const [phraseIndex, setPhraseIndex] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (!isReady && prev >= 90) return 90;
        if (prev >= 100) {
          clearInterval(progressInterval);
          return 100;
        }
        return prev + 2;
      });
    }, 45);

    const phraseInterval = setInterval(() => {
      setPhraseIndex((prev) => (prev + 1) % LOADING_PHRASES.length);
    }, 600);

    return () => {
      clearInterval(progressInterval);
      clearInterval(phraseInterval);
    };
  }, [isReady]);

  useEffect(() => {
    if (!isReady) return;
    const fastForward = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(fastForward);
          return 100;
        }
        return Math.min(100, prev + 5);
      });
    }, 20);
    return () => clearInterval(fastForward);
  }, [isReady]);

  useEffect(() => {
    if (progress >= 100 && isReady && onComplete) {
      const timeout = setTimeout(() => {
        onComplete();
      }, 300);
      return () => clearTimeout(timeout);
    }
    return undefined;
  }, [progress, isReady, onComplete]);

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-surface-sunken/95 backdrop-blur-xl px-6 text-center select-none overflow-hidden">
      {/* Background Ambient Radial Glow */}
      <div className="absolute w-[500px] h-[500px] bg-accent/10 rounded-full blur-[120px] pointer-events-none animate-pulse" />

      {/* Runic Magic Circle Engine */}
      <div className="relative w-44 h-44 mb-8 flex items-center justify-center">
        {/* Outer Rotating Dash Ring */}
        <svg
          className="absolute inset-0 w-full h-full text-accent/30 animate-[spin_12s_linear_infinite]"
          viewBox="0 0 100 100"
        >
          <circle
            cx="50"
            cy="50"
            r="46"
            fill="none"
            stroke="currentColor"
            strokeWidth="1"
            strokeDasharray="4 6"
          />
        </svg>

        {/* Counter-rotating Inner Rune Ring */}
        <svg
          className="absolute inset-2 w-[calc(100%-16px)] h-[calc(100%-16px)] text-accent/50 animate-[spin_8s_linear_infinite_reverse]"
          viewBox="0 0 100 100"
        >
          <circle
            cx="50"
            cy="50"
            r="44"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeDasharray="12 4"
          />
          <polygon
            points="50,10 85,75 15,75"
            fill="none"
            stroke="currentColor"
            strokeWidth="0.75"
            className="opacity-40"
          />
          <polygon
            points="50,90 15,25 85,25"
            fill="none"
            stroke="currentColor"
            strokeWidth="0.75"
            className="opacity-40"
          />
        </svg>

        {/* Inner Glowing Core Sigil */}
        <div className="w-16 h-16 rounded-full bg-accent/10 border border-accent/40 flex items-center justify-center shadow-float animate-pulse">
          <span className="font-display text-2xl text-accent font-bold tracking-widest">
            ❖
          </span>
        </div>
      </div>

      {/* Title & Phase Text */}
      <div className="space-y-3 max-w-md">
        {scenarioTitle && (
          <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-content-faint block">
            {scenarioTitle}
          </span>
        )}
        <h2 className="font-display text-2xl md:text-3xl text-content font-bold tracking-wide transition-all duration-300 min-h-[40px] flex items-center justify-center">
          {LOADING_PHRASES[phraseIndex]}
        </h2>
        <p className="font-mono text-xs text-accent tracking-widest uppercase">
          INITIATING PLAYTHROUGH • {progress}%
        </p>
      </div>

      {/* Atmospheric Progress Bar */}
      <div className="mt-8 w-64 h-1 bg-surface-sunken rounded-full overflow-hidden border border-border-strong relative">
        <div
          className="h-full bg-primary transition-all duration-75 ease-out rounded-full shadow-float"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
};
