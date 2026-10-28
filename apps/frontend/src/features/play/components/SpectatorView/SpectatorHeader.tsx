export interface SpectatorHeaderProps {
  scenarioTitle: string;
  isLive: boolean;
}

export function SpectatorHeader({ scenarioTitle, isLive }: SpectatorHeaderProps) {
  return (
    <header className="border-b border-stone-800/60 px-6 py-4 flex items-center justify-between">
      <div>
        <h1 className="font-serif text-lg font-semibold text-amber-200">
          {scenarioTitle}
        </h1>
        <p className="font-mono text-[11px] text-stone-500 uppercase tracking-wider">
          Spectating (Read-Only)
        </p>
      </div>
      {isLive && (
        <span className="flex items-center gap-1.5 font-mono text-[11px] text-amber-400 uppercase tracking-wider">
          <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
          Live
        </span>
      )}
    </header>
  );
}
