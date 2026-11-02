import { IconCoins } from "@tabler/icons-react";
import type { FantasyStatusStripProps } from "./FantasyStatusStrip.types";

export function FantasyStatusStrip({ status }: FantasyStatusStripProps) {
  const energyPercent = status.energy
    ? Math.min(100, Math.max(0, (status.energy.current / status.energy.max) * 100))
    : 0;

  return (
    <aside className="fixed top-[88px] left-0 right-0 z-30 h-9 shrink-0 bg-[#100D0B] border-b border-[#382E25] flex items-center px-4 md:px-8 overflow-x-auto no-scrollbar whitespace-nowrap font-mono select-none">
      <div className="flex items-center gap-6 text-[11px] tracking-wide text-[#B5A593]">
        {status.locale && <div className="flex items-center gap-1.5">
          <span className="text-[#8C7A6B] uppercase font-mono text-[10px]">Locale:</span>
          <span className="text-[#F5EEDB] font-serif font-medium text-[13px]">{status.locale}</span>
        </div>}
        {status.energy && (
          <>
            <span className="text-[#382E25]">/</span>
            <div className="flex items-center gap-1.5">
              <span className="text-[#8C7A6B] uppercase font-mono text-[10px]">Energy:</span>
              <div className="w-20 h-1.5 bg-[#1F1914] rounded overflow-hidden inline-flex border border-[#382E25]">
                <div
                  className="bg-gradient-to-r from-[#9C6D37] to-[#D4AF37] h-full rounded"
                  style={{ width: `${energyPercent}%` }}
                />
              </div>
              <span className="text-[#EDE0CA]">{status.energy.current} / {status.energy.max}</span>
            </div>
          </>
        )}
        {status.vault && (
          <>
            <span className="text-[#382E25]">/</span>
            <div className="flex items-center gap-1.5">
              <span className="text-[#8C7A6B] uppercase font-mono text-[10px]">Coins:</span>
              <span className="text-[#C5A059] font-medium flex items-center gap-1">
                <IconCoins size={13} /> {status.vault.label}
              </span>
            </div>
          </>
        )}
      </div>
    </aside>
  );
}
